import { useState, useEffect, useCallback } from 'react';
import { membersAPI, plansAPI, hourBankAPI, claimsAPI } from '../lib/api';
import api from '../lib/api';
import { toast } from 'sonner';
import {
  Users,
  Plus,
  Search,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  UserX,
  UserPlus,
  Clock,
  FileText,
  Upload,
  DollarSign,
  CalendarClock,
  ShieldAlert,
  ScrollText,
  ArrowRight,
  ArrowLeft,
  X,
  Timer,
  TrendingDown,
  TrendingUp,
  Minus,
  Activity,
  Heart,
  Shield,
  Eye,
  UserCheck,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '../components/ui/tabs';

const INITIAL_FORM = {
  member_id: '', first_name: '', last_name: '', dob: '', gender: 'M',
  group_id: '', plan_id: '', effective_date: new Date().toISOString().split('T')[0],
  termination_date: '', relationship: 'subscriber',
};

export default function Members() {
  const [members, setMembers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);
  const [auditTrail, setAuditTrail] = useState([]);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);

  // Hour bank state
  const [hourBankData, setHourBankData] = useState(null);
  const [hourBankLoading, setHourBankLoading] = useState(false);

  // 360 view states
  const [accumulators, setAccumulators] = useState(null);
  const [claimsHistory, setClaimsHistory] = useState([]);
  const [dependentsData, setDependentsData] = useState(null);
  const [selectedClaimEOB, setSelectedClaimEOB] = useState(null);
  const [eobLoading, setEobLoading] = useState(false);

  // Reconciliation state
  const [reconData, setReconData] = useState(null);
  const [reconLoading, setReconLoading] = useState(false);

  // Retro-term state
  const [retroTerms, setRetroTerms] = useState([]);
  const [retroLoading, setRetroLoading] = useState(false);

  // Age-out state
  const [ageOutAlerts, setAgeOutAlerts] = useState([]);
  const [ageOutLoading, setAgeOutLoading] = useState(false);

  // Pending eligibility
  const [processingElig, setProcessingElig] = useState(false);

  const fetchMembers = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchTerm) params.search = searchTerm;
      const res = await membersAPI.list(params);
      setMembers(res.data);
    } catch { toast.error('Failed to load members'); }
    finally { setLoading(false); }
  }, [searchTerm]);

  const fetchPlans = useCallback(async () => {
    try { const res = await plansAPI.list(); setPlans(res.data); } catch {}
  }, []);

  useEffect(() => { fetchMembers(); fetchPlans(); }, [fetchMembers, fetchPlans]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const data = { ...form };
      if (!data.termination_date) delete data.termination_date;
      await membersAPI.create(data);
      toast.success('Member created');
      setShowCreate(false);
      setForm(INITIAL_FORM);
      fetchMembers();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create member'); }
    finally { setSaving(false); }
  };

  const openDetail = async (member) => {
    setSelectedMember(member);
    setShowDetail(true);
    setHourBankData(null);
    setAccumulators(null);
    setClaimsHistory([]);
    setDependentsData(null);
    setSelectedClaimEOB(null);
    // Load all 360 data in parallel
    const mid = member.member_id;
    Promise.all([
      membersAPI.auditTrail(mid).then(r => setAuditTrail(r.data)).catch(() => setAuditTrail([])),
      membersAPI.accumulators(mid).then(r => setAccumulators(r.data)).catch(() => setAccumulators(null)),
      hourBankAPI.getLedger(mid).then(r => setHourBankData(r.data)).catch(() => setHourBankData(null)),
      membersAPI.claimsHistory(mid).then(r => setClaimsHistory(r.data)).catch(() => setClaimsHistory([])),
      membersAPI.dependents(mid).then(r => setDependentsData(r.data)).catch(() => setDependentsData(null)),
    ]);
  };

  const fetchHourBank = async (memberId) => {
    setHourBankLoading(true);
    try {
      const res = await hourBankAPI.getLedger(memberId);
      setHourBankData(res.data);
    } catch { setHourBankData(null); }
    finally { setHourBankLoading(false); }
  };

  const fetchReconciliation = async () => {
    setReconLoading(true);
    try {
      const res = await membersAPI.reconciliation();
      setReconData(res.data);
    } catch { toast.error('Failed to load reconciliation'); }
    finally { setReconLoading(false); }
  };

  const fetchRetroTerms = async () => {
    setRetroLoading(true);
    try {
      const res = await membersAPI.retroTerms();
      setRetroTerms(res.data);
    } catch { toast.error('Failed to load retro-terms'); }
    finally { setRetroLoading(false); }
  };

  const fetchAgeOutAlerts = async () => {
    setAgeOutLoading(true);
    try {
      const res = await membersAPI.ageOutAlerts();
      setAgeOutAlerts(res.data);
    } catch { toast.error('Failed to load age-out alerts'); }
    finally { setAgeOutLoading(false); }
  };

  const handleUploadFeed = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const res = await membersAPI.uploadTpaFeed(file);
      toast.success(`TPA feed uploaded: ${res.data.members_loaded} members`);
      fetchReconciliation();
    } catch { toast.error('Failed to upload TPA feed'); }
    e.target.value = '';
  };

  const handleRequestRefund = async (memberId) => {
    setSaving(true);
    try {
      const res = await membersAPI.requestRefund(memberId);
      toast.success(`Provider refund requested: ${fmt(res.data.total_recovery)} across ${res.data.claims_affected} claims`);
      fetchRetroTerms();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to request refund'); }
    finally { setSaving(false); }
  };

  const handleProcessPendingElig = async () => {
    setProcessingElig(true);
    try {
      const res = await membersAPI.processPendingEligibility();
      toast.success(`Processed: ${res.data.released} released, ${res.data.denied} denied, ${res.data.still_pending} still pending`);
    } catch { toast.error('Failed to process pending eligibility'); }
    finally { setProcessingElig(false); }
  };

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0);

  const loadClaimEOB = async (claimId) => {
    setEobLoading(true);
    try {
      const res = await claimsAPI.get(claimId);
      setSelectedClaimEOB(res.data);
    } catch { toast.error('Failed to load claim detail'); }
    finally { setEobLoading(false); }
  };

  const AccumBar = ({ label, used, max, color = '#1A3636', icon: Icon }) => {
    const pct = max > 0 ? Math.min((used / max) * 100, 100) : 0;
    return (
      <div className="h-[56px]" data-testid={`accum-${label.toLowerCase().replace(/[^a-z]/g, '-')}`}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1.5">
            {Icon && <Icon className="h-3 w-3" style={{ color }} />}
            <span className="text-[10px] uppercase tracking-wider text-[#8A8A85]">{label}</span>
          </div>
          <span className="text-[10px] font-['JetBrains_Mono'] tabular-nums text-[#64645F]">{fmt(used)} / {fmt(max)}</span>
        </div>
        <div className="h-2 bg-[#E2E2DF] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: pct > 80 ? '#C24A3B' : pct > 50 ? '#C9862B' : color }}
          />
        </div>
        <div className="flex justify-end mt-0.5">
          <span className="text-[9px] tabular-nums text-[#8A8A85]">{pct.toFixed(0)}%</span>
        </div>
      </div>
    );
  };

  const StatusBadge = ({ status }) => {
    const cls = status === 'approved' ? 'badge-approved' :
                status === 'denied' ? 'bg-[#C24A3B] text-white border-0' :
                status === 'pending_review' ? 'bg-[#C9862B] text-white border-0' :
                status === 'duplicate' ? 'bg-[#5C2D91] text-white border-0' :
                'bg-[#F0F0EA] text-[#64645F] border-0';
    return <Badge className={`${cls} text-[10px]`}>{status?.replace(/_/g, ' ')}</Badge>;
  };

  const AUDIT_ICONS = {
    member_added: UserPlus,
    member_updated: RefreshCw,
    member_terminated: UserX,
    member_retro_terminated: AlertTriangle,
    refund_requested: DollarSign,
    tpa_feed_uploaded: Upload,
  };

  return (
    <div className="space-y-6" data-testid="members-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Eligibility Management</h1>
          <p className="text-sm text-[#64645F] mt-1">Census, reconciliation, retro-terms, and dependent lifecycle</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleProcessPendingElig} disabled={processingElig} variant="outline" className="btn-secondary" data-testid="process-pending-btn">
            {processingElig ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Clock className="h-4 w-4 mr-2" />}
            Process Pending Eligibility
          </Button>
          <Button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="add-member-btn">
            <Plus className="h-4 w-4 mr-2" />Add Member
          </Button>
        </div>
      </div>

      <Tabs defaultValue="census" className="w-full">
        <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF]">
          <TabsTrigger value="census" className="data-[state=active]:bg-white text-xs" data-testid="tab-census"><Users className="h-3.5 w-3.5 mr-1" />Census</TabsTrigger>
          <TabsTrigger value="reconciliation" className="data-[state=active]:bg-white text-xs" onClick={fetchReconciliation} data-testid="tab-reconciliation"><ShieldAlert className="h-3.5 w-3.5 mr-1" />Reconciliation</TabsTrigger>
          <TabsTrigger value="retro-terms" className="data-[state=active]:bg-white text-xs" onClick={fetchRetroTerms} data-testid="tab-retro-terms"><AlertTriangle className="h-3.5 w-3.5 mr-1" />Retro-Terms</TabsTrigger>
          <TabsTrigger value="age-out" className="data-[state=active]:bg-white text-xs" onClick={fetchAgeOutAlerts} data-testid="tab-age-out"><CalendarClock className="h-3.5 w-3.5 mr-1" />Age-Out</TabsTrigger>
        </TabsList>

        {/* === CENSUS TAB === */}
        <TabsContent value="census" className="mt-4 space-y-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchMembers()}
                placeholder="Search by name or member ID..."
                className="input-field pl-10"
                data-testid="member-search"
              />
            </div>
            <Button onClick={fetchMembers} variant="outline" className="btn-secondary"><RefreshCw className="h-4 w-4" /></Button>
          </div>

          <div className="container-card p-0 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-48"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
            ) : members.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48"><Users className="h-10 w-10 text-[#E2E2DF] mb-3" /><p className="text-[#8A8A85]">No members found</p></div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead>Member ID</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>DOB</TableHead>
                    <TableHead>Relationship</TableHead>
                    <TableHead>Group</TableHead>
                    <TableHead>Effective</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[40px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.map((m) => (
                    <TableRow key={m.member_id} className="table-row hover:bg-[#F7F7F4] transition-colors cursor-pointer" onClick={() => openDetail(m)} data-testid={`member-row-${m.member_id}`}>
                      <TableCell className="font-['JetBrains_Mono'] text-xs">{m.member_id}</TableCell>
                      <TableCell className="font-medium">{m.first_name} {m.last_name}</TableCell>
                      <TableCell className="text-xs">{m.dob}</TableCell>
                      <TableCell className="capitalize text-xs">{m.relationship}</TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-xs">{m.group_id?.slice(0, 8) || '—'}</TableCell>
                      <TableCell className="text-xs">{m.effective_date}</TableCell>
                      <TableCell><Badge className={m.status === 'active' ? 'badge-approved' : 'bg-[#F0F0EA] text-[#8A8A85] border-0'}>{m.status}</Badge></TableCell>
                      <TableCell><ChevronRight className="h-4 w-4 text-[#8A8A85]" /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* === RECONCILIATION TAB === */}
        <TabsContent value="reconciliation" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Eligibility Reconciliation</h2>
              <p className="text-xs text-[#8A8A85]">Compare MGU Census vs Latest TPA 834 Feed</p>
            </div>
            <div className="flex gap-2">
              <label className="cursor-pointer">
                <input type="file" accept=".txt,.csv,.834" onChange={handleUploadFeed} className="hidden" data-testid="upload-tpa-feed" />
                <span className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E2E2DF] text-sm text-[#64645F] hover:bg-[#F7F7F4] transition-colors">
                  <Upload className="h-4 w-4" />Upload TPA Feed
                </span>
              </label>
              <Button onClick={fetchReconciliation} variant="outline" className="btn-secondary"><RefreshCw className="h-4 w-4" /></Button>
            </div>
          </div>

          {reconLoading ? (
            <div className="flex items-center justify-center h-48"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
          ) : !reconData ? (
            <div className="container-card flex flex-col items-center justify-center h-48">
              <ShieldAlert className="h-10 w-10 text-[#E2E2DF] mb-3" />
              <p className="text-[#8A8A85]">Click tab or refresh to load reconciliation data</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="metric-card"><div className="flex items-center gap-2 mb-2"><Users className="h-4 w-4 text-[#64645F]" /><span className="metric-label">Census Count</span></div><p className="metric-value">{reconData.census_count}</p></div>
                <div className="metric-card"><div className="flex items-center gap-2 mb-2"><FileText className="h-4 w-4 text-[#64645F]" /><span className="metric-label">TPA Feed Count</span></div><p className="metric-value">{reconData.tpa_feed_count}</p></div>
                <div className="metric-card"><div className="flex items-center gap-2 mb-2"><UserX className="h-4 w-4 text-[#C24A3B]" /><span className="metric-label">Ghost Members</span></div><p className="metric-value text-[#C24A3B]">{reconData.ghost_members?.length || 0}</p></div>
                <div className="metric-card"><div className="flex items-center gap-2 mb-2"><UserPlus className="h-4 w-4 text-[#C9862B]" /><span className="metric-label">Unmatched Members</span></div><p className="metric-value text-[#C9862B]">{reconData.unmatched_members?.length || 0}</p></div>
              </div>

              {reconData.ghost_members?.length > 0 && (
                <div className="container-card p-0 overflow-hidden" data-testid="ghost-members-table">
                  <div className="p-4 border-b border-[#E2E2DF] bg-[#FFF5F5]">
                    <div className="flex items-center gap-2"><UserX className="h-4 w-4 text-[#C24A3B]" /><h3 className="text-sm font-medium text-[#C24A3B]">Ghost Members (On Census, Missing from TPA Feed)</h3></div>
                  </div>
                  <Table>
                    <TableHeader><TableRow className="table-header"><TableHead>Member ID</TableHead><TableHead>Name</TableHead><TableHead>Group</TableHead><TableHead>Effective</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {reconData.ghost_members.map((m) => (
                        <TableRow key={m.member_id} className="table-row"><TableCell className="font-['JetBrains_Mono'] text-xs">{m.member_id}</TableCell><TableCell>{m.first_name} {m.last_name}</TableCell><TableCell className="text-xs">{m.group_id?.slice(0,8) || '—'}</TableCell><TableCell className="text-xs">{m.effective_date}</TableCell></TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {reconData.unmatched_members?.length > 0 && (
                <div className="container-card p-0 overflow-hidden" data-testid="unmatched-members-table">
                  <div className="p-4 border-b border-[#E2E2DF] bg-[#FFFBF5]">
                    <div className="flex items-center gap-2"><UserPlus className="h-4 w-4 text-[#C9862B]" /><h3 className="text-sm font-medium text-[#C9862B]">Unmatched Members (On TPA Feed, Missing from Census)</h3></div>
                  </div>
                  <Table>
                    <TableHeader><TableRow className="table-header"><TableHead>Member ID</TableHead><TableHead>Name</TableHead><TableHead>Group</TableHead><TableHead>Effective</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {reconData.unmatched_members.map((m) => (
                        <TableRow key={m.member_id} className="table-row"><TableCell className="font-['JetBrains_Mono'] text-xs">{m.member_id}</TableCell><TableCell>{m.first_name} {m.last_name}</TableCell><TableCell className="text-xs">{m.group_id?.slice(0,8) || '—'}</TableCell><TableCell className="text-xs">{m.effective_date}</TableCell></TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {reconData.ghost_members?.length === 0 && reconData.unmatched_members?.length === 0 && (
                <div className="container-card flex items-center justify-center h-32">
                  <p className="text-sm text-[#4B6E4E] font-medium">Census and TPA Feed are fully reconciled</p>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* === RETRO-TERMS TAB === */}
        <TabsContent value="retro-terms" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Retro-Term Monitor & Clawback</h2>
              <p className="text-xs text-[#8A8A85]">Members terminated retroactively with paid claims after term date</p>
            </div>
            <Button onClick={fetchRetroTerms} variant="outline" className="btn-secondary"><RefreshCw className="h-4 w-4" /></Button>
          </div>

          {retroLoading ? (
            <div className="flex items-center justify-center h-48"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
          ) : retroTerms.length === 0 ? (
            <div className="container-card flex flex-col items-center justify-center h-48">
              <AlertTriangle className="h-10 w-10 text-[#E2E2DF] mb-3" />
              <p className="text-[#8A8A85]">No retro-terminations with clawback claims found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {retroTerms.map((rt) => (
                <div key={rt.member_id} className="container-card" data-testid={`retro-term-${rt.member_id}`}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-[#C24A3B]" />
                        <h3 className="text-sm font-medium text-[#1C1C1A]">{rt.first_name} {rt.last_name}</h3>
                        <Badge className="bg-[#C24A3B] text-white border-0 text-[10px]">Retro-Termed</Badge>
                        {rt.refund_status && <Badge className="bg-[#C9862B] text-white border-0 text-[10px]">{rt.refund_status === 'requested' ? 'Refund Requested' : rt.refund_status}</Badge>}
                      </div>
                      <p className="text-xs text-[#8A8A85] mt-1">Member: {rt.member_id} | Term Date: {rt.termination_date}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-[#8A8A85]">Total Clawback</p>
                      <p className="text-lg font-semibold font-['JetBrains_Mono'] text-[#C24A3B]">{fmt(rt.clawback_total)}</p>
                    </div>
                  </div>

                  <Table>
                    <TableHeader><TableRow className="table-header"><TableHead>Claim #</TableHead><TableHead>Service Date</TableHead><TableHead>Provider</TableHead><TableHead className="text-right">Paid</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {rt.claims_after_term.map((c) => (
                        <TableRow key={c.id} className="table-row">
                          <TableCell className="font-['JetBrains_Mono'] text-xs">{c.claim_number}</TableCell>
                          <TableCell className="text-xs">{c.service_date_from}</TableCell>
                          <TableCell className="text-xs">{c.provider_name}</TableCell>
                          <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#C24A3B]">{fmt(c.total_paid)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  <div className="mt-4 flex justify-end">
                    <Button
                      onClick={() => handleRequestRefund(rt.member_id)}
                      disabled={saving || rt.refund_status === 'requested'}
                      className={rt.refund_status === 'requested' ? 'bg-[#8A8A85] text-white' : 'bg-[#C24A3B] hover:bg-[#a93e31] text-white'}
                      data-testid={`request-refund-${rt.member_id}`}
                    >
                      {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <DollarSign className="h-4 w-4 mr-2" />}
                      {rt.refund_status === 'requested' ? 'Refund Already Requested' : 'Request Provider Refund'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* === AGE-OUT TAB === */}
        <TabsContent value="age-out" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Dependent Age-Out Alerts</h2>
              <p className="text-xs text-[#8A8A85]">Dependents turning 26 within the next 30 days</p>
            </div>
            <Button onClick={fetchAgeOutAlerts} variant="outline" className="btn-secondary"><RefreshCw className="h-4 w-4" /></Button>
          </div>

          {ageOutLoading ? (
            <div className="flex items-center justify-center h-48"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
          ) : ageOutAlerts.length === 0 ? (
            <div className="container-card flex flex-col items-center justify-center h-48">
              <CalendarClock className="h-10 w-10 text-[#E2E2DF] mb-3" />
              <p className="text-[#8A8A85]">No dependents aging out in the next 30 days</p>
            </div>
          ) : (
            <div className="container-card p-0 overflow-hidden" data-testid="age-out-table">
              <div className="p-4 border-b border-[#E2E2DF] bg-[#FFFBF5]">
                <div className="flex items-center gap-2"><CalendarClock className="h-4 w-4 text-[#C9862B]" /><h3 className="text-sm font-medium text-[#C9862B]">{ageOutAlerts.length} Dependent{ageOutAlerts.length !== 1 ? 's' : ''} Approaching Age 26</h3></div>
              </div>
              <Table>
                <TableHeader><TableRow className="table-header"><TableHead>Member ID</TableHead><TableHead>Name</TableHead><TableHead>DOB</TableHead><TableHead>Age-Out Date</TableHead><TableHead>Days Until</TableHead><TableHead>Group</TableHead></TableRow></TableHeader>
                <TableBody>
                  {ageOutAlerts.map((a) => (
                    <TableRow key={a.member_id} className="table-row" data-testid={`age-out-${a.member_id}`}>
                      <TableCell className="font-['JetBrains_Mono'] text-xs">{a.member_id}</TableCell>
                      <TableCell className="font-medium">{a.first_name} {a.last_name}</TableCell>
                      <TableCell className="text-xs">{a.dob}</TableCell>
                      <TableCell className="text-xs font-medium">{a.age_out_date}</TableCell>
                      <TableCell>
                        <Badge className={a.days_until <= 7 ? 'bg-[#C24A3B] text-white border-0 text-[10px]' : a.days_until <= 14 ? 'bg-[#C9862B] text-white border-0 text-[10px]' : 'bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]'}>
                          {a.days_until} day{a.days_until !== 1 ? 's' : ''}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">{a.group_id?.slice(0,8) || '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* CREATE MEMBER MODAL */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Add Member</DialogTitle>
            <DialogDescription>Add a new member to the eligibility census</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid grid-cols-2 gap-4 py-4">
              <div className="space-y-2"><Label>Member ID *</Label><Input value={form.member_id} onChange={(e) => setForm({ ...form, member_id: e.target.value })} className="input-field" required data-testid="member-id-input" /></div>
              <div className="space-y-2"><Label>Gender</Label>
                <Select value={form.gender} onValueChange={(v) => setForm({ ...form, gender: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="M">Male</SelectItem><SelectItem value="F">Female</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>First Name *</Label><Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className="input-field" required data-testid="member-first-name" /></div>
              <div className="space-y-2"><Label>Last Name *</Label><Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} className="input-field" required data-testid="member-last-name" /></div>
              <div className="space-y-2"><Label>DOB *</Label><Input type="date" value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} className="input-field" required data-testid="member-dob" /></div>
              <div className="space-y-2"><Label>Relationship</Label>
                <Select value={form.relationship} onValueChange={(v) => setForm({ ...form, relationship: v })}>
                  <SelectTrigger data-testid="member-relationship"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="subscriber">Subscriber</SelectItem><SelectItem value="spouse">Spouse</SelectItem><SelectItem value="child">Child</SelectItem><SelectItem value="dependent">Dependent</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Group ID</Label><Input value={form.group_id} onChange={(e) => setForm({ ...form, group_id: e.target.value })} className="input-field" data-testid="member-group-id" /></div>
              <div className="space-y-2"><Label>Plan</Label>
                <Select value={form.plan_id} onValueChange={(v) => setForm({ ...form, plan_id: v })}>
                  <SelectTrigger data-testid="member-plan"><SelectValue placeholder="Select plan..." /></SelectTrigger>
                  <SelectContent>{plans.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Effective Date *</Label><Input type="date" value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} className="input-field" required data-testid="member-eff-date" /></div>
              <div className="space-y-2"><Label>Termination Date</Label><Input type="date" value={form.termination_date} onChange={(e) => setForm({ ...form, termination_date: e.target.value })} className="input-field" data-testid="member-term-date" /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</Button>
              <Button type="submit" disabled={saving} className="btn-primary" data-testid="submit-member-btn">
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Add Member'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* MEMBER 360 DETAIL VIEW */}
      <Dialog open={showDetail} onOpenChange={(open) => { setShowDetail(open); if (!open) setSelectedClaimEOB(null); }}>
        <DialogContent className="max-w-5xl max-h-[92vh] overflow-hidden flex flex-col p-0">
          {selectedMember && (
            <>
              {/* ─── STATIC HEADER: Never moves when tabs change ─── */}
              <div className="flex-shrink-0 border-b border-[#E2E2DF] p-5 pb-4 bg-white" data-testid="member-360-header">
                {/* Row 1: Name + Status + Hour Bank inline */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-semibold text-[#1C1C1A] font-['Outfit']" data-testid="member-360-name">
                        {selectedMember.first_name} {selectedMember.last_name}
                      </h2>
                      <Badge className={selectedMember.status === 'active' ? 'badge-approved' : selectedMember.status === 'termed_insufficient_hours' ? 'bg-[#C24A3B] text-white border-0 text-[10px]' : 'bg-[#F0F0EA] text-[#8A8A85] border-0 text-[10px]'} data-testid="member-360-status">
                        {selectedMember.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-[#8A8A85] mt-0.5">
                      <span className="font-['JetBrains_Mono']">{selectedMember.member_id}</span>
                      <span className="mx-1.5">|</span>{selectedMember.relationship}
                      <span className="mx-1.5">|</span>DOB: {selectedMember.dob}
                      <span className="mx-1.5">|</span>Eff: {selectedMember.effective_date}
                      {selectedMember.termination_date && <><span className="mx-1.5">|</span>Term: {selectedMember.termination_date}</>}
                    </p>
                  </div>
                  {/* Hour Bank Status Chip */}
                  <div className="flex-shrink-0" data-testid="header-hour-bank-status">
                    {hourBankData ? (
                      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
                        hourBankData.at_risk ? 'bg-[#FFF5F5] border-[#C24A3B]/30' :
                        hourBankData.total_balance > 0 ? 'bg-[#F0F7F1] border-[#4B6E4E]/30' :
                        'bg-[#F7F7F4] border-[#E2E2DF]'
                      }`}>
                        <Timer className={`h-3.5 w-3.5 ${hourBankData.at_risk ? 'text-[#C24A3B]' : 'text-[#4B6E4E]'}`} />
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Hour Bank</p>
                          <p className={`text-sm font-bold tabular-nums ${hourBankData.at_risk ? 'text-[#C24A3B]' : 'text-[#1A3636]'}`}>
                            {hourBankData.total_balance.toFixed(1)} hrs
                          </p>
                        </div>
                        {hourBankData.at_risk && (
                          <Badge className="bg-[#C24A3B] text-white border-0 text-[9px] ml-1" data-testid="header-at-risk">Hold</Badge>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#F7F7F4] border border-[#E2E2DF]">
                        <Timer className="h-3.5 w-3.5 text-[#8A8A85]" />
                        <span className="text-xs text-[#8A8A85]">No bank</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Row 2: Financial Accumulators — always visible */}
                <div className="grid grid-cols-3 gap-4" data-testid="financial-accumulators">
                  {accumulators ? (
                    <>
                      <AccumBar label="Individual Deductible" used={accumulators.individual_deductible.used} max={accumulators.individual_deductible.max} color="#1A3636" icon={Shield} />
                      <AccumBar label="Family Deductible" used={accumulators.family_deductible.used} max={accumulators.family_deductible.max} color="#4A6FA5" icon={Users} />
                      <AccumBar label="Out-of-Pocket Max" used={accumulators.oop_max.used} max={accumulators.oop_max.max} color="#C9862B" icon={DollarSign} />
                    </>
                  ) : (
                    <>
                      {[1,2,3].map(i => (
                        <div key={i} className="h-[56px] animate-pulse">
                          <div className="h-2 bg-[#E2E2DF] rounded w-24 mb-2" />
                          <div className="h-2 bg-[#E2E2DF] rounded-full" />
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>

              {/* ─── SCROLLABLE TABS AREA ─── */}
              <div className="flex-1 overflow-y-auto p-5 pt-3">
                <Tabs defaultValue="claims-history" className="w-full" onValueChange={(v) => {
                  if (v === 'hour-bank' && !hourBankData) fetchHourBank(selectedMember.member_id);
                  if (v !== 'claims-history') setSelectedClaimEOB(null);
                }}>
                  <TabsList className="bg-[#F0F0EA] h-9 mb-3">
                    <TabsTrigger value="claims-history" className="data-[state=active]:bg-white text-xs" data-testid="detail-tab-claims">
                      <FileText className="h-3.5 w-3.5 mr-1" />Claims History
                    </TabsTrigger>
                    <TabsTrigger value="dependents" className="data-[state=active]:bg-white text-xs" data-testid="detail-tab-dependents">
                      <Heart className="h-3.5 w-3.5 mr-1" />Family / Dependents
                    </TabsTrigger>
                    <TabsTrigger value="hour-bank" className="data-[state=active]:bg-white text-xs" data-testid="detail-tab-hour-bank">
                      <Timer className="h-3.5 w-3.5 mr-1" />Hour Bank
                    </TabsTrigger>
                    <TabsTrigger value="audit" className="data-[state=active]:bg-white text-xs" data-testid="detail-tab-audit">
                      <ScrollText className="h-3.5 w-3.5 mr-1" />Audit Trail
                    </TabsTrigger>
                  </TabsList>

                  {/* ═══ CLAIMS HISTORY TAB ═══ */}
                  <TabsContent value="claims-history" className="mt-0" data-testid="member-claims-history">
                    {selectedClaimEOB ? (
                      /* Inline EOB View */
                      <div className="space-y-3" data-testid="inline-eob">
                        <Button variant="ghost" size="sm" onClick={() => setSelectedClaimEOB(null)} className="text-xs text-[#64645F] -ml-2" data-testid="back-to-claims-btn">
                          <ArrowLeft className="h-3 w-3 mr-1" />Back to Claims
                        </Button>
                        <div className="bg-[#F7F7F4] rounded-xl p-4 border border-[#E2E2DF]">
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <p className="text-sm font-semibold text-[#1C1C1A] font-['Outfit']">Claim EOB: {selectedClaimEOB.claim_number}</p>
                              <p className="text-[10px] text-[#8A8A85]">{selectedClaimEOB.provider_name} | {selectedClaimEOB.service_date_from}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <StatusBadge status={selectedClaimEOB.status} />
                              {selectedClaimEOB.eligibility_source && selectedClaimEOB.eligibility_source !== 'standard_hours' && (
                                <Badge className={
                                  selectedClaimEOB.eligibility_source === 'bridge_payment' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                                  selectedClaimEOB.eligibility_source === 'reserve_draw' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                                  selectedClaimEOB.eligibility_source === 'insufficient' ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                                  'bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]'
                                }>{selectedClaimEOB.eligibility_source?.replace(/_/g, ' ')}</Badge>
                              )}
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-3 mb-3">
                            <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                              <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Billed</p>
                              <p className="text-sm font-bold font-['JetBrains_Mono'] tabular-nums">{fmt(selectedClaimEOB.total_billed)}</p>
                            </div>
                            <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                              <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Allowed / Paid</p>
                              <p className="text-sm font-bold font-['JetBrains_Mono'] tabular-nums text-[#4B6E4E]">{fmt(selectedClaimEOB.total_paid)}</p>
                            </div>
                            <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                              <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Member Resp</p>
                              <p className="text-sm font-bold font-['JetBrains_Mono'] tabular-nums text-[#C9862B]">{fmt(selectedClaimEOB.member_responsibility)}</p>
                            </div>
                          </div>
                          {/* Service Lines */}
                          {selectedClaimEOB.service_lines?.length > 0 && (
                            <Table>
                              <TableHeader><TableRow className="border-[#E2E2DF]">
                                <TableHead className="text-[10px]">CPT</TableHead>
                                <TableHead className="text-[10px]">Description</TableHead>
                                <TableHead className="text-right text-[10px]">Billed</TableHead>
                                <TableHead className="text-right text-[10px]">Allowed</TableHead>
                                <TableHead className="text-right text-[10px]">Paid</TableHead>
                              </TableRow></TableHeader>
                              <TableBody>
                                {selectedClaimEOB.service_lines.map((sl, i) => (
                                  <TableRow key={i} className="h-[36px]">
                                    <TableCell className="font-['JetBrains_Mono'] text-xs">{sl.cpt_code}</TableCell>
                                    <TableCell className="text-xs truncate max-w-[180px]">{sl.description || '—'}</TableCell>
                                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{fmt(sl.billed_amount)}</TableCell>
                                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{fmt(sl.allowed_amount)}</TableCell>
                                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums text-[#4B6E4E]">{fmt(sl.paid_amount)}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                          {/* Adjudication Notes */}
                          {selectedClaimEOB.adjudication_notes?.length > 0 && (
                            <div className="mt-3 bg-white rounded-lg p-3 border border-[#E2E2DF]">
                              <p className="text-[10px] uppercase tracking-wider text-[#8A8A85] mb-1.5">Adjudication Notes</p>
                              {selectedClaimEOB.adjudication_notes.map((n, i) => (
                                <p key={i} className="text-xs text-[#64645F] leading-relaxed">{n}</p>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      /* Claims List */
                      <>
                        {claimsHistory.length === 0 ? (
                          <div className="bg-[#F7F7F4] rounded-lg p-8 text-center">
                            <FileText className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" />
                            <p className="text-sm text-[#8A8A85]">No claims history for this member</p>
                          </div>
                        ) : (
                          <Table>
                            <TableHeader>
                              <TableRow className="border-[#E2E2DF]">
                                <TableHead>Claim #</TableHead>
                                <TableHead>Service Date</TableHead>
                                <TableHead>Provider</TableHead>
                                <TableHead>CPT Codes</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Source</TableHead>
                                <TableHead className="text-right">Billed</TableHead>
                                <TableHead className="text-right">Paid</TableHead>
                                <TableHead className="w-[32px]"></TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {claimsHistory.map((c) => (
                                <TableRow
                                  key={c.id}
                                  className="table-row h-[44px] hover:bg-[#F7F7F4] cursor-pointer transition-colors"
                                  onClick={() => loadClaimEOB(c.id)}
                                  data-testid={`claim-history-row-${c.id}`}
                                >
                                  <TableCell className="font-['JetBrains_Mono'] text-xs">{c.claim_number}</TableCell>
                                  <TableCell className="text-xs tabular-nums">{c.service_date}</TableCell>
                                  <TableCell className="text-xs truncate max-w-[120px]">{c.provider_name || '—'}</TableCell>
                                  <TableCell className="text-xs font-['JetBrains_Mono']">{c.cpt_codes?.join(', ') || '—'}</TableCell>
                                  <TableCell><StatusBadge status={c.status} /></TableCell>
                                  <TableCell>
                                    {c.eligibility_source && c.eligibility_source !== 'standard_hours' ? (
                                      <Badge className={
                                        c.eligibility_source === 'bridge_payment' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                                        c.eligibility_source === 'reserve_draw' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                                        c.eligibility_source === 'insufficient' ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                                        'bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]'
                                      }>{c.eligibility_source?.replace(/_/g, ' ')}</Badge>
                                    ) : <span className="text-[10px] text-[#8A8A85]">—</span>}
                                  </TableCell>
                                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{fmt(c.total_billed)}</TableCell>
                                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums text-[#4B6E4E]">{fmt(c.total_paid)}</TableCell>
                                  <TableCell><Eye className="h-3.5 w-3.5 text-[#8A8A85]" /></TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        )}
                      </>
                    )}
                  </TabsContent>

                  {/* ═══ FAMILY / DEPENDENTS TAB ═══ */}
                  <TabsContent value="dependents" className="mt-0" data-testid="member-dependents">
                    {!dependentsData ? (
                      <div className="bg-[#F7F7F4] rounded-lg p-8 text-center">
                        <Users className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" />
                        <p className="text-sm text-[#8A8A85]">Loading family data...</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {/* Subscriber card */}
                        <div className="bg-[#F0F7F1] border border-[#4B6E4E]/20 rounded-xl p-4" data-testid="subscriber-card">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-lg bg-[#4B6E4E] flex items-center justify-center">
                              <UserCheck className="h-4 w-4 text-white" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-semibold text-[#1C1C1A]">{dependentsData.subscriber.first_name} {dependentsData.subscriber.last_name}</p>
                                <Badge className="bg-[#4B6E4E] text-white border-0 text-[9px]">Subscriber</Badge>
                                <Badge className={dependentsData.subscriber.status === 'active' ? 'badge-approved text-[9px]' : 'bg-[#F0F0EA] text-[#8A8A85] border-0 text-[9px]'}>{dependentsData.subscriber.status}</Badge>
                              </div>
                              <p className="text-[10px] text-[#64645F]">
                                <span className="font-['JetBrains_Mono']">{dependentsData.subscriber.member_id}</span>
                                <span className="mx-1">|</span>DOB: {dependentsData.subscriber.dob}
                                <span className="mx-1">|</span>Eff: {dependentsData.subscriber.effective_date}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-[10px] text-[#8A8A85]">Household Size</p>
                              <p className="text-lg font-bold tabular-nums text-[#1A3636]">{dependentsData.household_size}</p>
                            </div>
                          </div>
                        </div>

                        {/* Dependents list */}
                        {dependentsData.dependents.length === 0 ? (
                          <div className="bg-[#F7F7F4] rounded-lg p-6 text-center">
                            <p className="text-sm text-[#8A8A85]">No dependents in this household</p>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {dependentsData.dependents.map((dep) => (
                              <div key={dep.member_id} className="flex items-center gap-3 bg-[#F7F7F4] rounded-lg p-3 h-[56px]" data-testid={`dependent-row-${dep.member_id}`}>
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                  dep.relationship === 'spouse' ? 'bg-[#4A6FA5]' :
                                  dep.relationship === 'child' ? 'bg-[#C9862B]' :
                                  'bg-[#8A8A85]'
                                }`}>
                                  <Heart className="h-3.5 w-3.5 text-white" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <p className="text-sm font-medium text-[#1C1C1A]">{dep.first_name} {dep.last_name}</p>
                                    <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px] capitalize">{dep.relationship}</Badge>
                                    <Badge className={dep.status === 'active' ? 'badge-approved text-[9px]' : 'bg-[#F0F0EA] text-[#8A8A85] border-0 text-[9px]'}>{dep.status}</Badge>
                                  </div>
                                  <p className="text-[10px] text-[#8A8A85]">
                                    <span className="font-['JetBrains_Mono']">{dep.member_id}</span>
                                    <span className="mx-1">|</span>DOB: {dep.dob}
                                  </p>
                                </div>
                                <div className="text-right flex-shrink-0">
                                  <p className="text-[10px] text-[#8A8A85]">Effective</p>
                                  <p className="text-xs font-medium tabular-nums">{dep.effective_date}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Cross-Accumulation: Family Deductible Contributions */}
                        {accumulators?.family_deductible?.contributions?.length > 0 && (
                          <div className="bg-white rounded-xl border border-[#E2E2DF] p-4" data-testid="family-cross-accumulation">
                            <div className="flex items-center gap-2 mb-3">
                              <Activity className="h-4 w-4 text-[#4A6FA5]" />
                              <p className="text-xs font-medium text-[#1C1C1A]">Family Deductible Cross-Accumulation</p>
                              <span className="text-[10px] text-[#8A8A85] ml-auto font-['JetBrains_Mono'] tabular-nums">
                                {fmt(accumulators.family_deductible.used)} / {fmt(accumulators.family_deductible.max)}
                              </span>
                            </div>
                            <div className="h-3 bg-[#E2E2DF] rounded-full overflow-hidden mb-3">
                              <div
                                className="h-full rounded-full bg-[#4A6FA5] transition-all duration-500"
                                style={{ width: `${accumulators.family_deductible.max > 0 ? Math.min((accumulators.family_deductible.used / accumulators.family_deductible.max) * 100, 100) : 0}%` }}
                              />
                            </div>
                            <div className="space-y-1.5">
                              {accumulators.family_deductible.contributions.map((c) => {
                                const pct = accumulators.family_deductible.max > 0 ? (c.contribution / accumulators.family_deductible.max) * 100 : 0;
                                return (
                                  <div key={c.member_id} className="flex items-center gap-2 h-[28px]" data-testid={`contrib-${c.member_id}`}>
                                    <span className="text-xs w-28 truncate">{c.name}</span>
                                    <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px] capitalize w-16 justify-center">{c.relationship}</Badge>
                                    <div className="flex-1 h-1.5 bg-[#E2E2DF] rounded-full overflow-hidden">
                                      <div className="h-full rounded-full bg-[#4A6FA5]" style={{ width: `${pct}%` }} />
                                    </div>
                                    <span className="text-[10px] font-['JetBrains_Mono'] tabular-nums w-14 text-right">{fmt(c.contribution)}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </TabsContent>

                  {/* ═══ HOUR BANK TAB ═══ */}
                  <TabsContent value="hour-bank" className="mt-0" data-testid="member-hour-bank">
                  {hourBankLoading ? (
                    <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">Loading hour bank...</p></div>
                  ) : hourBankData ? (
                    <div className="space-y-4">
                      {/* Multi-Tier Balance Summary — fixed height to prevent jitter */}
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="hour-bank-summary">
                        <div className="bg-[#F7F7F4] rounded-lg p-3 h-[72px]">
                          <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Current</p>
                          <p className={`text-lg font-bold tabular-nums ${hourBankData.current_balance < 0 ? 'text-[#C24A3B]' : 'text-[#1A3636]'}`} data-testid="hour-bank-current">
                            {hourBankData.current_balance.toFixed(1)} hrs
                          </p>
                        </div>
                        <div className="bg-[#F7F7F4] rounded-lg p-3 h-[72px]">
                          <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Reserve</p>
                          <p className="text-lg font-bold tabular-nums text-[#4A6FA5]" data-testid="hour-bank-reserve">
                            {hourBankData.reserve_balance.toFixed(1)} hrs
                          </p>
                        </div>
                        <div className="bg-[#F7F7F4] rounded-lg p-3 h-[72px]">
                          <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Threshold</p>
                          <p className="text-lg font-bold tabular-nums text-[#1C1C1A]" data-testid="hour-bank-threshold">
                            {hourBankData.threshold > 0 ? `${hourBankData.threshold} hrs` : '—'}
                          </p>
                        </div>
                        <div className="bg-[#F7F7F4] rounded-lg p-3 h-[72px]">
                          <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Burn Rate</p>
                          <p className="text-lg font-bold tabular-nums text-[#C9862B]" data-testid="hour-bank-burn-rate">
                            {hourBankData.burn_rate.toFixed(1)}/mo
                          </p>
                        </div>
                        <div className="bg-[#F7F7F4] rounded-lg p-3 h-[72px]">
                          <p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Months Left</p>
                          <p className={`text-lg font-bold tabular-nums ${hourBankData.months_remaining < 2 ? 'text-[#C24A3B]' : hourBankData.months_remaining < 4 ? 'text-[#C9862B]' : 'text-[#4B6E4E]'}`} data-testid="hour-bank-months">
                            {hourBankData.months_remaining > 99 ? '99+' : hourBankData.months_remaining.toFixed(1)}
                          </p>
                        </div>
                      </div>

                      {/* At Risk / Eligibility Source badges */}
                      <div className="flex items-center gap-2 h-[28px]" data-testid="hour-bank-status-row">
                        {hourBankData.at_risk && (
                          <Badge className="bg-[#C24A3B] text-white border-0 text-[10px]" data-testid="at-risk-badge">
                            <AlertTriangle className="h-3 w-3 mr-1" />At Risk
                          </Badge>
                        )}
                        <Badge className={
                          hourBankData.eligibility_source === 'bridge_payment' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                          hourBankData.eligibility_source === 'reserve_draw' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                          hourBankData.eligibility_source === 'insufficient' ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                          'bg-[#4B6E4E] text-white border-0 text-[10px]'
                        } data-testid="eligibility-source-badge">
                          {hourBankData.eligibility_source === 'bridge_payment' ? 'Bridge Payment' :
                           hourBankData.eligibility_source === 'reserve_draw' ? 'Reserve Draw' :
                           hourBankData.eligibility_source === 'insufficient' ? 'Insufficient' :
                           'Standard Hours'}
                        </Badge>
                        <span className="text-[10px] text-[#8A8A85] ml-auto tabular-nums">Total: {hourBankData.total_balance.toFixed(1)} hrs</span>
                      </div>

                      {/* Bridge Payment Card */}
                      {hourBankData.bridge.enabled && hourBankData.bridge.eligible && (
                        <div className="bg-[#F3EBF9] border border-[#5C2D91]/30 rounded-lg p-4" data-testid="bridge-payment-card">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                <DollarSign className="h-4 w-4 text-[#5C2D91]" />
                                <p className="text-sm font-medium text-[#5C2D91]">Bridge Payment Available</p>
                              </div>
                              <p className="text-xs text-[#64645F] mt-1">
                                Member is <span className="font-semibold tabular-nums">{hourBankData.bridge.hours_short.toFixed(1)} hrs</span> short.
                                Cost: <span className="font-['JetBrains_Mono'] font-semibold">${hourBankData.bridge.cost.toFixed(2)}</span> at ${hourBankData.bridge.rate_per_hour}/hr.
                              </p>
                            </div>
                            <Button
                              onClick={async () => {
                                setSaving(true);
                                try {
                                  const res = await hourBankAPI.bridgePayment(selectedMember.member_id);
                                  toast.success(`Bridge payment logged: +${res.data.hours_added.toFixed(1)} hrs, $${res.data.cost.toFixed(2)} — Status: Active`);
                                  fetchHourBank(selectedMember.member_id);
                                } catch (err) { toast.error(err.response?.data?.detail || 'Bridge payment failed'); }
                                finally { setSaving(false); }
                              }}
                              disabled={saving}
                              size="sm"
                              className="bg-[#5C2D91] hover:bg-[#4a2475] text-white text-xs flex-shrink-0"
                              data-testid="execute-bridge-btn"
                            >
                              {saving ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <ArrowRight className="h-3 w-3 mr-1" />}
                              Execute Bridge
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Manual Hour Entry Form */}
                      <div className="bg-[#F7F7F4] rounded-lg p-3" data-testid="manual-entry-form">
                        <p className="text-xs font-medium text-[#64645F] mb-2">Manual Entry</p>
                        <div className="flex items-end gap-2">
                          <div className="flex-1 space-y-1">
                            <Label className="text-[10px]">Hours</Label>
                            <Input type="number" step="0.5" placeholder="e.g. 8.0" className="input-field h-8 text-xs" data-testid="manual-hours-input" id="manual-hours" />
                          </div>
                          <div className="flex-[2] space-y-1">
                            <Label className="text-[10px]">Description</Label>
                            <Input placeholder="Reason for adjustment" className="input-field h-8 text-xs" data-testid="manual-desc-input" id="manual-desc" />
                          </div>
                          <Button
                            onClick={async () => {
                              const hoursEl = document.getElementById('manual-hours');
                              const descEl = document.getElementById('manual-desc');
                              const hrs = parseFloat(hoursEl?.value);
                              const desc = descEl?.value || 'Manual adjustment';
                              if (!hrs || isNaN(hrs)) { toast.error('Enter valid hours'); return; }
                              setSaving(true);
                              try {
                                await hourBankAPI.manualEntry(selectedMember.member_id, hrs, desc);
                                toast.success(`${hrs > 0 ? '+' : ''}${hrs} hours logged`);
                                if (hoursEl) hoursEl.value = '';
                                if (descEl) descEl.value = '';
                                fetchHourBank(selectedMember.member_id);
                              } catch (err) { toast.error(err.response?.data?.detail || 'Failed to add hours'); }
                              finally { setSaving(false); }
                            }}
                            disabled={saving}
                            size="sm"
                            className="btn-primary h-8 text-xs"
                            data-testid="submit-manual-entry-btn"
                          >
                            {saving ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3 mr-1" />}
                            Add
                          </Button>
                        </div>
                      </div>

                      {/* Ledger entries */}
                      <div>
                        <h4 className="text-xs font-medium text-[#64645F] mb-2">Ledger</h4>
                        {hourBankData.entries.length === 0 ? (
                          <div className="bg-[#F7F7F4] rounded-lg p-6 text-center">
                            <p className="text-sm text-[#8A8A85]">No hour bank entries yet</p>
                          </div>
                        ) : (
                          <div className="space-y-1.5 max-h-[220px] overflow-y-auto" data-testid="hour-bank-ledger">
                            {hourBankData.entries.map((entry) => (
                              <div key={entry.id} className="flex items-center gap-3 bg-[#F7F7F4] rounded-lg px-3 py-2 h-[44px]" data-testid={`hb-entry-${entry.id}`}>
                                <div className={`w-6 h-6 rounded flex items-center justify-center flex-shrink-0 ${
                                  entry.entry_type === 'work_hours' ? 'bg-[#2D6A4F]' :
                                  entry.entry_type === 'monthly_deduction' ? 'bg-[#C24A3B]' :
                                  entry.entry_type === 'bridge_payment' ? 'bg-[#5C2D91]' :
                                  entry.entry_type === 'manual_adjustment' ? 'bg-[#C9862B]' :
                                  'bg-[#4A6FA5]'
                                }`}>
                                  {entry.entry_type === 'work_hours' ? <TrendingUp className="h-3 w-3 text-white" /> :
                                   entry.entry_type === 'monthly_deduction' ? <TrendingDown className="h-3 w-3 text-white" /> :
                                   entry.entry_type === 'bridge_payment' ? <DollarSign className="h-3 w-3 text-white" /> :
                                   <Minus className="h-3 w-3 text-white" />}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs font-medium text-[#1C1C1A] truncate">{entry.description}</p>
                                </div>
                                <div className="text-right flex-shrink-0 w-16">
                                  <p className="text-[10px] tabular-nums text-[#8A8A85]">C:{entry.current_after?.toFixed(1) ?? '—'}</p>
                                </div>
                                <div className="text-right flex-shrink-0 w-16">
                                  <p className="text-[10px] tabular-nums text-[#8A8A85]">R:{entry.reserve_after?.toFixed(1) ?? '—'}</p>
                                </div>
                                <div className="text-right flex-shrink-0 w-20">
                                  <p className={`text-xs font-bold tabular-nums ${entry.hours >= 0 ? 'text-[#2D6A4F]' : 'text-[#C24A3B]'}`}>
                                    {entry.hours >= 0 ? '+' : ''}{entry.hours.toFixed(1)}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-[#F7F7F4] rounded-lg p-6 text-center">
                      <Timer className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" />
                      <p className="text-sm text-[#8A8A85]">No hour bank data available</p>
                    </div>
                  )}
                  </TabsContent>

                  {/* ═══ AUDIT TRAIL TAB ═══ */}
                  <TabsContent value="audit" className="mt-0" data-testid="member-audit-trail">
                    {auditTrail.length === 0 ? (
                      <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">No audit trail entries</p></div>
                    ) : (
                      <div className="space-y-2 max-h-[400px] overflow-y-auto">
                        {auditTrail.map((entry) => {
                          const Icon = AUDIT_ICONS[entry.action] || FileText;
                          return (
                            <div key={entry.id} className="flex items-start gap-3 bg-[#F7F7F4] rounded-lg p-3" data-testid={`audit-entry-${entry.id}`}>
                              <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${
                                entry.action === 'member_retro_terminated' ? 'bg-[#C24A3B]' :
                                entry.action === 'member_terminated' ? 'bg-[#C9862B]' :
                                entry.action === 'refund_requested' ? 'bg-[#5C2D91]' :
                                'bg-[#1A3636]'
                              }`}>
                                <Icon className="h-3.5 w-3.5 text-white" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <p className="text-xs font-medium text-[#1C1C1A] capitalize">{entry.action.replace(/_/g, ' ')}</p>
                                  <span className="text-[10px] text-[#8A8A85]">{new Date(entry.timestamp).toLocaleString()}</span>
                                </div>
                                {entry.details && (
                                  <p className="text-[10px] text-[#64645F] mt-0.5">
                                    {entry.details.source && `Source: ${entry.details.source}`}
                                    {entry.details.effective_date && ` | Effective: ${entry.details.effective_date}`}
                                    {entry.details.termination_date && ` | Term: ${entry.details.termination_date}`}
                                    {entry.details.total_recovery && ` | Recovery: ${fmt(entry.details.total_recovery)}`}
                                    {entry.details.claim_count && ` | Claims: ${entry.details.claim_count}`}
                                  </p>
                                )}
                                <p className="text-[10px] text-[#8A8A85]">By: {entry.user_id}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
