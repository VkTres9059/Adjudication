import { useState, useEffect, useRef } from 'react';
import { aiAgentAPI, vapiAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Phone, PhoneOff, Send, RefreshCw, MessageSquare, AlertTriangle,
  User, Bot, Plus, CheckCircle2, Clock, ChevronRight,
  Shield, Mic, MicOff, Volume2, VolumeX, Radio,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

export default function AIAgent() {
  const [activeTab, setActiveTab] = useState('chat');
  const [sessions, setSessions] = useState([]);
  const [callLogs, setCallLogs] = useState([]);
  const [voiceCalls, setVoiceCalls] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [providerTaxId, setProviderTaxId] = useState('');
  const [memberId, setMemberId] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const messagesEndRef = useRef(null);

  // Voice state
  const [vapiConfig, setVapiConfig] = useState(null);
  const [vapiInstance, setVapiInstance] = useState(null);
  const [callActive, setCallActive] = useState(false);
  const [callConnecting, setCallConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState([]);
  const [callDuration, setCallDuration] = useState(0);
  const callTimerRef = useRef(null);

  useEffect(() => {
    fetchSessions();
    fetchCallLogs();
    fetchVapiConfig();
    fetchVoiceCalls();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      if (callTimerRef.current) clearInterval(callTimerRef.current);
      if (vapiInstance) {
        try { vapiInstance.stop(); } catch {}
      }
    };
  }, [vapiInstance]);

  const fetchSessions = async () => {
    try { const res = await aiAgentAPI.sessions(20); setSessions(res.data); } catch {}
  };
  const fetchCallLogs = async () => {
    try { const res = await aiAgentAPI.callLogs(); setCallLogs(res.data); } catch {}
  };
  const fetchVapiConfig = async () => {
    try { const res = await vapiAPI.getConfig(); setVapiConfig(res.data); } catch {}
  };
  const fetchVoiceCalls = async () => {
    try { const res = await vapiAPI.calls(20); setVoiceCalls(res.data); } catch {}
  };

  const startNewSession = () => {
    setCurrentSession(null);
    setMessages([]);
    setAuthenticated(false);
    setProviderTaxId('');
    setMemberId('');
  };

  const loadSession = async (sessionId) => {
    try {
      const res = await aiAgentAPI.sessionMessages(sessionId);
      setMessages(res.data);
      setCurrentSession(sessionId);
      setAuthenticated(true);
    } catch { toast.error('Failed to load session'); }
  };

  const handleAuth = () => {
    if (!providerTaxId.trim()) { toast.error('Provider Tax ID is required'); return; }
    setAuthenticated(true);
    toast.success('Provider authenticated');
  };

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg, timestamp: new Date().toISOString() }]);
    setSending(true);
    try {
      const res = await aiAgentAPI.chat({
        message: userMsg, session_id: currentSession,
        provider_tax_id: providerTaxId, member_id: memberId,
      });
      if (!currentSession) setCurrentSession(res.data.session_id);
      setMessages(prev => [...prev, {
        role: 'assistant', content: res.data.response,
        context_provided: res.data.context_provided, timestamp: new Date().toISOString(),
      }]);
      fetchSessions();
    } catch {
      toast.error('Failed to get response');
      setMessages(prev => [...prev, {
        role: 'assistant', content: 'I apologize, but I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    } finally { setSending(false); }
  };

  const handleEscalate = async () => {
    try {
      await aiAgentAPI.escalate({
        provider_tax_id: providerTaxId, member_id: memberId,
        query_summary: messages.length > 0 ? messages[messages.length - 1].content : 'Manual escalation',
        session_id: currentSession || '',
      });
      toast.success('Escalation ticket created');
      fetchCallLogs();
    } catch { toast.error('Failed to create escalation'); }
  };

  const resolveLog = async (logId) => {
    try { await aiAgentAPI.resolveCallLog(logId, 'Resolved via UI'); toast.success('Resolved'); fetchCallLogs(); }
    catch { toast.error('Failed to resolve'); }
  };

  // ── Voice Call Handlers ──
  const startVoiceCall = async () => {
    if (!vapiConfig?.assistant_id) {
      toast.error('Voice assistant not configured. Contact admin to set up Vapi.');
      return;
    }
    setCallConnecting(true);
    setVoiceTranscript([]);
    setCallDuration(0);

    try {
      const VapiModule = await import('@vapi-ai/web');
      const Vapi = VapiModule.default;
      const publicKey = process.env.REACT_APP_VAPI_PUBLIC_KEY;
      if (!publicKey) {
        toast.error('Vapi public key not configured');
        setCallConnecting(false);
        return;
      }
      const vapi = new Vapi(publicKey);

      vapi.on('call-start', () => {
        setCallActive(true);
        setCallConnecting(false);
        toast.success('Voice call connected');
        callTimerRef.current = setInterval(() => setCallDuration(d => d + 1), 1000);
      });

      vapi.on('call-end', () => {
        setCallActive(false);
        setCallConnecting(false);
        setIsSpeaking(false);
        if (callTimerRef.current) { clearInterval(callTimerRef.current); callTimerRef.current = null; }
        toast.info('Voice call ended');
        fetchVoiceCalls();
      });

      vapi.on('message', (msg) => {
        if (msg.type === 'transcript' && msg.transcriptType === 'final') {
          setVoiceTranscript(prev => [...prev, {
            role: msg.role, text: msg.transcript,
            timestamp: new Date().toISOString(),
          }]);
        }
        if (msg.type === 'speech-update') {
          setIsSpeaking(msg.status === 'started');
        }
      });

      vapi.on('error', (err) => {
        console.error('Vapi error:', err);
        setCallConnecting(false);
        toast.error('Voice call error: ' + (err?.message || 'Unknown'));
      });

      await vapi.start(vapiConfig.assistant_id);
      setVapiInstance(vapi);
    } catch (err) {
      console.error('Failed to start voice call:', err);
      setCallConnecting(false);
      toast.error('Failed to start voice call');
    }
  };

  const endVoiceCall = () => {
    if (vapiInstance) {
      try { vapiInstance.stop(); } catch {}
      setVapiInstance(null);
    }
    setCallActive(false);
    setCallConnecting(false);
    if (callTimerRef.current) { clearInterval(callTimerRef.current); callTimerRef.current = null; }
  };

  const toggleMute = () => {
    if (vapiInstance) {
      vapiInstance.setMuted(!isMuted);
      setIsMuted(!isMuted);
    }
  };

  const formatDuration = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="space-y-6" data-testid="ai-agent-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">AI Provider Agent</h1>
          <p className="text-sm text-[#64645F]">HIPAA-compliant AI assistant — text chat & voice calls</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-[#4B6E4E] text-white border-0 text-[10px]">GPT-5.2 Powered</Badge>
          <Badge className="bg-[#1A3636] text-white border-0 text-[10px]">HIPAA Compliant</Badge>
          {vapiConfig?.enabled && (
            <Badge className="bg-[#5C2D91] text-white border-0 text-[10px]" data-testid="vapi-badge">Vapi Voice</Badge>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-[#F0F0EA] p-1 rounded-xl">
          <TabsTrigger value="chat" className="data-[state=active]:bg-white text-sm" data-testid="tab-chat">
            <MessageSquare className="h-3.5 w-3.5 mr-1.5" />Text Agent
          </TabsTrigger>
          <TabsTrigger value="voice" className="data-[state=active]:bg-white text-sm" data-testid="tab-voice">
            <Phone className="h-3.5 w-3.5 mr-1.5" />Voice Agent
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-white text-sm" data-testid="tab-history">
            <Clock className="h-3.5 w-3.5 mr-1.5" />Sessions
          </TabsTrigger>
          <TabsTrigger value="call-logs" className="data-[state=active]:bg-white text-sm" data-testid="tab-call-logs">
            <AlertTriangle className="h-3.5 w-3.5 mr-1.5" />Call Logs
            {callLogs.filter(l => l.status === 'open').length > 0 && (
              <span className="ml-1.5 bg-[#C24A3B] text-white text-[9px] px-1.5 py-0.5 rounded-full">{callLogs.filter(l => l.status === 'open').length}</span>
            )}
          </TabsTrigger>
        </TabsList>

        {/* ── TEXT CHAT TAB ── */}
        <TabsContent value="chat" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-3 container-card p-3 max-h-[600px] overflow-y-auto">
              <Button variant="outline" size="sm" onClick={startNewSession} className="w-full text-xs mb-3" data-testid="new-session-btn">
                <Plus className="h-3 w-3 mr-1" />New Session
              </Button>
              <div className="space-y-1">
                {sessions.map(s => (
                  <button key={s.session_id} onClick={() => loadSession(s.session_id)}
                    className={`w-full text-left p-2 rounded-lg text-xs transition-colors ${currentSession === s.session_id ? 'bg-[#1A3636] text-white' : 'hover:bg-[#F0F0EA] text-[#64645F]'}`}>
                    <p className="truncate font-medium">{s.last_message}</p>
                    <p className="text-[10px] opacity-70">{s.message_count} msgs</p>
                  </button>
                ))}
                {sessions.length === 0 && <p className="text-[10px] text-[#8A8A85] text-center py-4">No sessions yet</p>}
              </div>
            </div>
            <div className="col-span-9">
              {!authenticated ? (
                <div className="container-card" data-testid="provider-auth-form">
                  <div className="flex items-center gap-3 mb-5">
                    <div className="w-10 h-10 bg-[#1A3636] rounded-lg flex items-center justify-center">
                      <Shield className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Provider Authentication</h3>
                      <p className="text-xs text-[#8A8A85]">Verify provider identity before accessing member records</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="space-y-2">
                      <Label>Provider Tax ID (TIN) *</Label>
                      <Input value={providerTaxId} onChange={e => setProviderTaxId(e.target.value)} placeholder="XX-XXXXXXX" className="input-field" data-testid="provider-tax-id" />
                    </div>
                    <div className="space-y-2">
                      <Label>Member ID (optional)</Label>
                      <Input value={memberId} onChange={e => setMemberId(e.target.value)} placeholder="Member ID" className="input-field" data-testid="member-id-input" />
                    </div>
                  </div>
                  <Button onClick={handleAuth} className="btn-primary" data-testid="auth-provider-btn">
                    <Shield className="h-4 w-4 mr-2" />Authenticate & Start
                  </Button>
                </div>
              ) : (
                <div className="container-card p-0 flex flex-col" style={{ height: '560px' }}>
                  <div className="flex items-center justify-between p-4 border-b border-[#E2E2DF]">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-[#1A3636] rounded-lg flex items-center justify-center">
                        <Bot className="h-4 w-4 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#1C1C1A]">FletchFlow Agent</p>
                        <p className="text-[10px] text-[#8A8A85]">TIN: {providerTaxId}{memberId ? ` | Member: ${memberId}` : ''}</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleEscalate} className="text-xs text-[#C24A3B]" data-testid="escalate-btn">
                      <AlertTriangle className="h-3 w-3 mr-1" />Escalate
                    </Button>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-messages">
                    {messages.length === 0 && (
                      <div className="text-center py-12">
                        <Bot className="h-12 w-12 text-[#E2E2DF] mx-auto mb-3" />
                        <p className="text-sm text-[#8A8A85]">Ask about eligibility, claim status, accumulators, or pre-certification</p>
                        <div className="flex flex-wrap gap-2 justify-center mt-4">
                          {['Is member active?', 'Claim status #', 'Deductible remaining?', 'Does CPT 55840 need auth?'].map(q => (
                            <button key={q} onClick={() => setInput(q)} className="text-[10px] px-3 py-1.5 bg-[#F0F0EA] rounded-full text-[#64645F] hover:bg-[#E2E2DF] transition-colors">
                              {q}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {messages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[75%] rounded-xl p-3 ${msg.role === 'user' ? 'bg-[#1A3636] text-white' : 'bg-[#F7F7F4] text-[#1C1C1A] border border-[#E2E2DF]'}`}>
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          <p className={`text-[9px] mt-1 ${msg.role === 'user' ? 'text-white/50' : 'text-[#8A8A85]'}`}>
                            {new Date(msg.timestamp).toLocaleTimeString()}
                            {msg.context_provided && <span className="ml-2 text-[#4B6E4E]">DB context used</span>}
                          </p>
                        </div>
                      </div>
                    ))}
                    {sending && (
                      <div className="flex justify-start">
                        <div className="bg-[#F7F7F4] rounded-xl p-3 border border-[#E2E2DF]">
                          <RefreshCw className="h-4 w-4 animate-spin text-[#8A8A85]" />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                  <div className="p-4 border-t border-[#E2E2DF]">
                    <div className="flex gap-2">
                      <Input value={memberId} onChange={e => setMemberId(e.target.value)} placeholder="Member ID" className="input-field w-32 text-xs" data-testid="chat-member-id" />
                      <Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendMessage()}
                        placeholder="Ask about eligibility, claims, accumulators..." className="input-field flex-1" data-testid="chat-input" />
                      <Button onClick={sendMessage} disabled={sending || !input.trim()} className="btn-primary" data-testid="send-btn">
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* ── VOICE AGENT TAB ── */}
        <TabsContent value="voice" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            {/* Voice Call Panel */}
            <div className="col-span-8">
              <div className="container-card">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${callActive ? 'bg-[#4B6E4E] animate-pulse' : 'bg-[#1A3636]'}`}>
                      <Phone className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Voice Provider Agent</h3>
                      <p className="text-xs text-[#8A8A85]">
                        {callActive ? `In call — ${formatDuration(callDuration)}` :
                         callConnecting ? 'Connecting...' : 'Ready for voice interaction'}
                      </p>
                    </div>
                  </div>
                  {callActive && (
                    <div className="flex items-center gap-2">
                      {isSpeaking && (
                        <Badge className="bg-[#4B6E4E] text-white border-0 text-[10px] animate-pulse">
                          <Volume2 className="h-3 w-3 mr-1" />Speaking
                        </Badge>
                      )}
                      <Badge className="bg-[#1A3636] text-white border-0 font-['JetBrains_Mono'] text-xs">
                        {formatDuration(callDuration)}
                      </Badge>
                    </div>
                  )}
                </div>

                {/* Call Controls */}
                <div className="flex items-center justify-center gap-4 mb-6">
                  {!callActive && !callConnecting ? (
                    <Button
                      onClick={startVoiceCall}
                      disabled={!vapiConfig?.enabled}
                      className="bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white rounded-full h-16 w-16 p-0"
                      data-testid="start-voice-call-btn"
                    >
                      <Phone className="h-7 w-7" />
                    </Button>
                  ) : (
                    <>
                      <Button
                        onClick={toggleMute}
                        variant="outline"
                        className={`rounded-full h-12 w-12 p-0 ${isMuted ? 'bg-[#C24A3B] text-white border-0' : ''}`}
                        data-testid="mute-btn"
                      >
                        {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                      </Button>
                      <Button
                        onClick={endVoiceCall}
                        className="bg-[#C24A3B] hover:bg-[#a53d30] text-white rounded-full h-16 w-16 p-0"
                        data-testid="end-voice-call-btn"
                      >
                        <PhoneOff className="h-7 w-7" />
                      </Button>
                    </>
                  )}
                </div>

                {callConnecting && (
                  <div className="text-center py-4">
                    <RefreshCw className="h-8 w-8 animate-spin text-[#1A3636] mx-auto mb-2" />
                    <p className="text-sm text-[#64645F]">Connecting to voice agent...</p>
                  </div>
                )}

                {!vapiConfig?.enabled && !callActive && (
                  <div className="text-center py-6 bg-[#FDF3E1] rounded-lg border border-[#F5D88E]">
                    <AlertTriangle className="h-6 w-6 text-[#C9862B] mx-auto mb-2" />
                    <p className="text-sm text-[#1C1C1A] font-medium">Voice Agent Not Configured</p>
                    <p className="text-xs text-[#64645F] mt-1">Vapi API key is required. Contact your administrator.</p>
                  </div>
                )}

                {/* Live Transcript */}
                {(callActive || voiceTranscript.length > 0) && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-[#1C1C1A] mb-3">Live Transcript</h4>
                    <div className="bg-[#F7F7F4] rounded-lg border border-[#E2E2DF] p-4 max-h-[300px] overflow-y-auto space-y-2" data-testid="voice-transcript">
                      {voiceTranscript.length === 0 && callActive && (
                        <p className="text-xs text-[#8A8A85] text-center py-4">Waiting for conversation...</p>
                      )}
                      {voiceTranscript.map((t, i) => (
                        <div key={i} className={`flex ${t.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] rounded-lg px-3 py-2 ${t.role === 'user' ? 'bg-[#1A3636] text-white' : 'bg-white border border-[#E2E2DF] text-[#1C1C1A]'}`}>
                            <p className="text-xs">{t.text}</p>
                            <p className={`text-[8px] mt-0.5 ${t.role === 'user' ? 'text-white/40' : 'text-[#8A8A85]'}`}>
                              {new Date(t.timestamp).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Voice Call History */}
            <div className="col-span-4">
              <div className="container-card">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-medium text-[#1C1C1A]">Recent Voice Calls</h4>
                  <Button variant="outline" size="sm" onClick={fetchVoiceCalls} className="text-[10px] h-6 px-2">
                    <RefreshCw className="h-3 w-3" />
                  </Button>
                </div>
                <div className="space-y-2 max-h-[500px] overflow-y-auto" data-testid="voice-calls-list">
                  {voiceCalls.length === 0 ? (
                    <p className="text-[10px] text-[#8A8A85] text-center py-6">No voice calls yet</p>
                  ) : voiceCalls.map(call => (
                    <div key={call.call_id} className="p-3 bg-[#F7F7F4] rounded-lg border border-[#E2E2DF]">
                      <div className="flex items-center justify-between mb-1">
                        <Badge className={`border-0 text-[9px] ${
                          call.status === 'ended' ? 'bg-[#4B6E4E] text-white' :
                          call.status === 'in-progress' ? 'bg-[#C9862B] text-white animate-pulse' :
                          'bg-[#8A8A85] text-white'
                        }`}>
                          {call.status}
                        </Badge>
                        <span className="text-[9px] text-[#8A8A85]">
                          {call.duration ? `${Math.round(call.duration / 60)}m` : '—'}
                        </span>
                      </div>
                      <p className="text-[10px] text-[#64645F] truncate">
                        {call.ended_reason || call.call_id?.slice(0, 12)}
                      </p>
                      <p className="text-[9px] text-[#8A8A85] mt-1">
                        {call.started_at ? new Date(call.started_at).toLocaleString() : '—'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* ── SESSIONS TAB ── */}
        <TabsContent value="history" className="mt-4">
          <div className="container-card">
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Recent Sessions</h3>
            {sessions.length === 0 ? (
              <p className="text-sm text-[#8A8A85] text-center py-8">No sessions recorded</p>
            ) : (
              <div className="space-y-2" data-testid="sessions-list">
                {sessions.map(s => (
                  <div key={s.session_id} onClick={() => { loadSession(s.session_id); setActiveTab('chat'); setAuthenticated(true); }}
                    className="flex items-center justify-between p-3 bg-[#F7F7F4] rounded-lg border border-[#E2E2DF] cursor-pointer hover:bg-[#F0F0EA] transition-colors">
                    <div className="flex items-center gap-3">
                      <MessageSquare className="h-4 w-4 text-[#64645F]" />
                      <div>
                        <p className="text-sm text-[#1C1C1A] truncate max-w-[400px]">{s.last_message}</p>
                        <p className="text-[10px] text-[#8A8A85]">{s.message_count} messages</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-[#8A8A85]">{new Date(s.last_timestamp).toLocaleString()}</span>
                      <ChevronRight className="h-4 w-4 text-[#8A8A85]" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* ── CALL LOGS TAB ── */}
        <TabsContent value="call-logs" className="mt-4">
          <div className="container-card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Escalation Call Logs</h3>
              <Button variant="outline" size="sm" onClick={fetchCallLogs} className="text-xs"><RefreshCw className="h-3 w-3 mr-1" />Refresh</Button>
            </div>
            {callLogs.length === 0 ? (
              <p className="text-sm text-[#8A8A85] text-center py-8">No escalations</p>
            ) : (
              <div className="space-y-2" data-testid="call-logs-list">
                {callLogs.map(log => (
                  <div key={log.id} className={`p-3 rounded-lg border ${log.status === 'open' ? 'bg-[#FDF3E1] border-[#F5D88E]' : 'bg-[#F7F7F4] border-[#E2E2DF]'}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge className={`border-0 text-[10px] ${log.status === 'open' ? 'bg-[#C9862B] text-white' : 'bg-[#4B6E4E] text-white'}`}>
                          {log.status.toUpperCase()}
                        </Badge>
                        {log.source === 'voice' && <Badge className="bg-[#5C2D91] text-white border-0 text-[9px]">Voice</Badge>}
                        <span className="text-xs text-[#64645F]">TIN: {log.provider_tax_id || 'N/A'}</span>
                        <span className="text-xs text-[#64645F]">Member: {log.member_id || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[#8A8A85]">{new Date(log.created_at).toLocaleString()}</span>
                        {log.status === 'open' && (
                          <Button variant="outline" size="sm" onClick={() => resolveLog(log.id)} className="text-[10px] h-6 px-2" data-testid={`resolve-${log.id}`}>
                            <CheckCircle2 className="h-3 w-3 mr-1" />Resolve
                          </Button>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-[#1C1C1A] mt-2">{log.query_summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
