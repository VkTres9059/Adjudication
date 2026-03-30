import { useState, useEffect, useRef } from 'react';
import { aiAgentAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Phone, Send, RefreshCw, MessageSquare, AlertTriangle,
  User, Bot, Plus, CheckCircle2, Clock, ChevronRight,
  Shield, Search,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Textarea } from '../components/ui/textarea';

export default function AIAgent() {
  const [activeTab, setActiveTab] = useState('chat');
  const [sessions, setSessions] = useState([]);
  const [callLogs, setCallLogs] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [providerTaxId, setProviderTaxId] = useState('');
  const [memberId, setMemberId] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchSessions();
    fetchCallLogs();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchSessions = async () => {
    try {
      const res = await aiAgentAPI.sessions(20);
      setSessions(res.data);
    } catch {}
  };

  const fetchCallLogs = async () => {
    try {
      const res = await aiAgentAPI.callLogs();
      setCallLogs(res.data);
    } catch {}
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
    if (!providerTaxId.trim()) {
      toast.error('Provider Tax ID is required for authentication');
      return;
    }
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
        message: userMsg,
        session_id: currentSession,
        provider_tax_id: providerTaxId,
        member_id: memberId,
      });
      if (!currentSession) {
        setCurrentSession(res.data.session_id);
      }
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.response,
        context_provided: res.data.context_provided,
        timestamp: new Date().toISOString(),
      }]);
      fetchSessions();
    } catch (err) {
      toast.error('Failed to get response');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleEscalate = async () => {
    try {
      await aiAgentAPI.escalate({
        provider_tax_id: providerTaxId,
        member_id: memberId,
        query_summary: messages.length > 0 ? messages[messages.length - 1].content : 'Manual escalation',
        session_id: currentSession || '',
      });
      toast.success('Escalation ticket created for Examiner Queue');
      fetchCallLogs();
    } catch { toast.error('Failed to create escalation'); }
  };

  const resolveLog = async (logId) => {
    try {
      await aiAgentAPI.resolveCallLog(logId, 'Resolved via UI');
      toast.success('Call log resolved');
      fetchCallLogs();
    } catch { toast.error('Failed to resolve'); }
  };

  return (
    <div className="space-y-6" data-testid="ai-agent-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">AI Provider Agent</h1>
          <p className="text-sm text-[#64645F]">HIPAA-compliant AI assistant for eligibility, claims, and pre-cert inquiries</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-[#4B6E4E] text-white border-0 text-[10px]">GPT-5.2 Powered</Badge>
          <Badge className="bg-[#1A3636] text-white border-0 text-[10px]">HIPAA Compliant</Badge>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-[#F0F0EA] p-1 rounded-xl">
          <TabsTrigger value="chat" className="data-[state=active]:bg-white text-sm" data-testid="tab-chat">
            <MessageSquare className="h-3.5 w-3.5 mr-1.5" />Live Agent
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

        <TabsContent value="chat" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            {/* Sidebar - Sessions */}
            <div className="col-span-3 container-card p-3 max-h-[600px] overflow-y-auto">
              <Button variant="outline" size="sm" onClick={startNewSession} className="w-full text-xs mb-3" data-testid="new-session-btn">
                <Plus className="h-3 w-3 mr-1" />New Session
              </Button>
              <div className="space-y-1">
                {sessions.map(s => (
                  <button key={s.session_id} onClick={() => loadSession(s.session_id)}
                    className={`w-full text-left p-2 rounded-lg text-xs transition-colors ${currentSession === s.session_id ? 'bg-[#1A3636] text-white' : 'hover:bg-[#F0F0EA] text-[#64645F]'}`}
                    data-testid={`session-${s.session_id}`}
                  >
                    <p className="truncate font-medium">{s.last_message}</p>
                    <p className="text-[10px] opacity-70">{s.message_count} msgs</p>
                  </button>
                ))}
                {sessions.length === 0 && <p className="text-[10px] text-[#8A8A85] text-center py-4">No sessions yet</p>}
              </div>
            </div>

            {/* Chat Area */}
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
                      <Input value={memberId} onChange={e => setMemberId(e.target.value)} placeholder="Member ID for context" className="input-field" data-testid="member-id-input" />
                    </div>
                  </div>
                  <Button onClick={handleAuth} className="btn-primary" data-testid="auth-provider-btn">
                    <Shield className="h-4 w-4 mr-2" />Authenticate & Start
                  </Button>
                </div>
              ) : (
                <div className="container-card p-0 flex flex-col" style={{ height: '560px' }}>
                  {/* Header */}
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

                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-messages">
                    {messages.length === 0 && (
                      <div className="text-center py-12">
                        <Bot className="h-12 w-12 text-[#E2E2DF] mx-auto mb-3" />
                        <p className="text-sm text-[#8A8A85]">Ask about eligibility, claim status, accumulators, or pre-certification</p>
                        <div className="flex flex-wrap gap-2 justify-center mt-4">
                          {['Is member active?', 'Claim status #', 'Deductible remaining?', 'Does CPT 55840 need auth?'].map(q => (
                            <button key={q} onClick={() => setInput(q)} className="text-[10px] px-3 py-1.5 bg-[#F0F0EA] rounded-full text-[#64645F] hover:bg-[#E2E2DF] transition-colors" data-testid={`quick-${q.replace(/\s+/g, '-').toLowerCase()}`}>
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

                  {/* Input */}
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
