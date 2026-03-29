import { useState, useEffect, useCallback } from 'react';
import { membersAPI, plansAPI } from '../lib/api';
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
  X,
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
    try {
      const res = await membersAPI.auditTrail(member.member_id);
      setAuditTrail(res.data);
    } catch { setAuditTrail([]); }
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

      {/* MEMBER DETAIL + AUDIT TRAIL */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedMember && (
            <>
              <DialogHeader>
                <DialogTitle className="font-['Outfit'] text-xl">{selectedMember.first_name} {selectedMember.last_name}</DialogTitle>
                <DialogDescription>Member ID: {selectedMember.member_id} | {selectedMember.relationship} | {selectedMember.status}</DialogDescription>
              </DialogHeader>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                <div className="bg-[#F7F7F4] rounded-lg p-3"><p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">DOB</p><p className="text-sm font-medium">{selectedMember.dob}</p></div>
                <div className="bg-[#F7F7F4] rounded-lg p-3"><p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Gender</p><p className="text-sm font-medium">{selectedMember.gender}</p></div>
                <div className="bg-[#F7F7F4] rounded-lg p-3"><p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Effective</p><p className="text-sm font-medium">{selectedMember.effective_date}</p></div>
                <div className="bg-[#F7F7F4] rounded-lg p-3"><p className="text-[10px] uppercase tracking-wider text-[#8A8A85]">Termination</p><p className="text-sm font-medium">{selectedMember.termination_date || '—'}</p></div>
              </div>

              {/* Member Audit Trail */}
              <div className="mt-6" data-testid="member-audit-trail">
                <div className="flex items-center gap-2 mb-3">
                  <ScrollText className="h-4 w-4 text-[#64645F]" />
                  <h3 className="text-sm font-medium text-[#1C1C1A]">Eligibility Audit Trail</h3>
                </div>
                {auditTrail.length === 0 ? (
                  <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">No audit trail entries</p></div>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
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
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
