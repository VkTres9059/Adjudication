import { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { checkRunAPI } from '../lib/api';
import {
  DollarSign, RefreshCw, FileText, Building2, Play, CheckCircle, AlertTriangle,
  Download, Banknote, CreditCard, Landmark, Plus, Trash2, ExternalLink, FileDown,
  ArrowRight, Zap, Save,
} from 'lucide-react';

export default function CheckRunManager() {
  const [asoGroups, setAsoGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('');
  const [pending, setPending] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [runDetail, setRunDetail] = useState(null);
  // Vendor payables
  const [vendorPayables, setVendorPayables] = useState([]);
  const [vpForm, setVpForm] = useState({ group_id: '', vendor_name: '', fee_type: 'pbm_access', description: '', amount: 0, frequency: 'monthly', is_active: true });
  const [vpSaving, setVpSaving] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [groupsRes, pendingRes, runsRes, vpRes] = await Promise.all([
        checkRunAPI.getAsoGroups(),
        checkRunAPI.getPending(selectedGroup || undefined),
        checkRunAPI.list(selectedGroup || undefined),
        checkRunAPI.vendorPayables(selectedGroup || undefined),
      ]);
      setAsoGroups(groupsRes.data);
      setPending(pendingRes.data);
      setRuns(runsRes.data);
      setVendorPayables(vpRes.data);
    } catch { toast.error('Failed to load check run data'); }
    finally { setLoading(false); }
  }, [selectedGroup]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(v || 0);

  const generateRequest = async (groupId) => {
    setGenerating(true);
    try {
      const res = await checkRunAPI.generateFundingRequest(groupId);
      toast.success(`Funding request generated — WF Txn: ${res.data.wf_funding_txn}`);
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to generate'); }
    finally { setGenerating(false); }
  };

  const confirmFunding = async (runId) => {
    try {
      await checkRunAPI.confirmFunding(runId);
      toast.success('Funding confirmed via Wells Fargo');
      fetchAll();
      if (showDetail) openDetail(runId);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to confirm'); }
  };

  const executeRun = async (runId) => {
    try {
      const res = await checkRunAPI.execute(runId);
      toast.success(`Check run executed — ACH: ${res.data.ach_batch}`);
      fetchAll();
      if (showDetail) openDetail(runId);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to execute'); }
  };

  const openDetail = async (runId) => {
    try {
      const res = await checkRunAPI.get(runId);
      setRunDetail(res.data);
      setShowDetail(true);
    } catch { toast.error('Failed to load details'); }
  };

  const downloadPdf = (runId) => {
    const token = localStorage.getItem('token');
    const url = checkRunAPI.pdfUrl(runId);
    window.open(`${url}?token=${token}`, '_blank');
  };

  // Vendor Payable actions
  const createVP = async () => {
    if (!vpForm.group_id || !vpForm.vendor_name || !vpForm.amount) { toast.error('Group, vendor name, and amount are required'); return; }
    setVpSaving(true);
    try {
      await checkRunAPI.createVendorPayable(vpForm);
      toast.success(`Vendor fee "${vpForm.vendor_name}" created`);
      setVpForm({ group_id: '', vendor_name: '', fee_type: 'pbm_access', description: '', amount: 0, frequency: 'monthly', is_active: true });
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create'); }
    finally { setVpSaving(false); }
  };

  const deleteVP = async (id) => {
    try { await checkRunAPI.deleteVendorPayable(id); toast.success('Vendor fee deleted'); fetchAll(); }
    catch { toast.error('Failed to delete'); }
  };

  const totalPending = pending.reduce((s, g) => s + g.provider_payable, 0);
  const totalVendorFees = pending.reduce((s, g) => s + (g.vendor_fees_total || 0), 0);
  const totalClaims = pending.reduce((s, g) => s + g.claim_count, 0);
  const totalFunding = pending.reduce((s, g) => s + (g.total_funding_required || g.provider_payable), 0);

  const statusColor = (s) => {
    switch (s) {
      case 'pending_funding': return 'bg-[#C9862B] text-white';
      case 'funded': return 'bg-[#4A6FA5] text-white';
      case 'executed': return 'bg-[#4B6E4E] text-white';
      default: return 'bg-[#8A8A85] text-white';
    }
  };

  const feeTypeLabel = (t) => {
    const m = { pbm_access: 'PBM Access', telehealth_pepm: 'Telehealth PEPM', network_access: 'Network Access', admin_fee: 'Admin Fee', other: 'Other' };
    return m[t] || t;
  };

  return (
    <div className="space-y-6" data-testid="check-run-manager">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Check Run Manager</h1>
          <p className="text-sm text-[#64645F] mt-1">ASO claim aggregation, Wells Fargo settlement, and vendor disbursement</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedGroup || 'all'} onValueChange={(v) => setSelectedGroup(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-[200px] input-field text-sm" data-testid="group-filter-select"><SelectValue placeholder="All ASO Groups" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Groups</SelectItem>
              {asoGroups.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={fetchAll} variant="outline" className="btn-secondary" data-testid="refresh-check-runs"><RefreshCw className="h-4 w-4 mr-2" />Refresh</Button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="metric-card" data-testid="metric-aso-groups">
          <div className="flex items-center gap-2 mb-2"><Building2 className="h-4 w-4 text-[#64645F]" /><span className="metric-label">ASO Groups</span></div>
          <p className="metric-value">{asoGroups.length}</p>
        </div>
        <div className="metric-card" data-testid="metric-pending-claims">
          <div className="flex items-center gap-2 mb-2"><FileText className="h-4 w-4 text-[#C9862B]" /><span className="metric-label">Claims Pending</span></div>
          <p className="metric-value">{totalClaims}</p>
        </div>
        <div className="metric-card" data-testid="metric-pending-amount">
          <div className="flex items-center gap-2 mb-2"><DollarSign className="h-4 w-4 text-[#4B6E4E]" /><span className="metric-label">Claims Payable</span></div>
          <p className="metric-value font-['JetBrains_Mono']">{fmt(totalPending)}</p>
        </div>
        <div className="metric-card" data-testid="metric-vendor-fees">
          <div className="flex items-center gap-2 mb-2"><Banknote className="h-4 w-4 text-[#5C2D91]" /><span className="metric-label">Vendor Fees</span></div>
          <p className="metric-value font-['JetBrains_Mono']">{fmt(totalVendorFees)}</p>
        </div>
        <div className="metric-card" data-testid="metric-total-funding">
          <div className="flex items-center gap-2 mb-2"><Landmark className="h-4 w-4 text-[#C24A3B]" /><span className="metric-label">Total Funding</span></div>
          <p className="metric-value font-['JetBrains_Mono']">{fmt(totalFunding)}</p>
        </div>
      </div>

      <Tabs defaultValue="pending" className="w-full">
        <TabsList className="bg-[#F0F0EA] p-1 rounded-xl">
          <TabsTrigger value="pending" className="data-[state=active]:bg-white text-sm" data-testid="tab-pending"><FileText className="h-3.5 w-3.5 mr-1.5" />Pending Runs</TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-white text-sm" data-testid="tab-history"><CreditCard className="h-3.5 w-3.5 mr-1.5" />Run History</TabsTrigger>
          <TabsTrigger value="vendors" className="data-[state=active]:bg-white text-sm" data-testid="tab-vendor-payables"><Banknote className="h-3.5 w-3.5 mr-1.5" />Vendor Payables</TabsTrigger>
        </TabsList>

        {/* ═══ PENDING RUNS TAB ═══ */}
        <TabsContent value="pending" className="mt-4 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>
          ) : pending.length === 0 ? (
            <div className="bg-[#F7F7F4] rounded-lg p-8 text-center"><CheckCircle className="h-8 w-8 text-[#4B6E4E] mx-auto mb-2" /><p className="text-sm text-[#8A8A85]">No approved claims pending a check run</p></div>
          ) : (
            pending.map((g) => (
              <div key={g.group_id} className="container-card" data-testid={`pending-group-${g.group_id}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <Building2 className="h-5 w-5 text-[#1A3636]" />
                    <div>
                      <p className="font-medium text-sm text-[#1C1C1A]">{g.group_name}</p>
                      <p className="text-[10px] text-[#8A8A85]">{g.claim_count} claims | {g.providers?.length || 0} providers | {g.members?.length || 0} members</p>
                    </div>
                  </div>
                  <Button onClick={() => generateRequest(g.group_id)} disabled={generating} className="btn-primary text-xs" data-testid={`gen-funding-${g.group_id}`}>
                    {generating ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Landmark className="h-3 w-3 mr-1" />}
                    Generate Funding Request
                  </Button>
                </div>

                {/* Financial Summary */}
                <div className="grid grid-cols-5 gap-4 text-sm mb-4">
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Total Billed</p><p className="font-['JetBrains_Mono'] font-semibold">{fmt(g.total_billed)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Member Resp.</p><p className="font-['JetBrains_Mono'] font-semibold">{fmt(g.member_resp)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Provider Payable</p><p className="font-['JetBrains_Mono'] font-semibold text-[#4B6E4E]">{fmt(g.provider_payable)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Vendor Fees</p><p className="font-['JetBrains_Mono'] font-semibold text-[#5C2D91]">{fmt(g.vendor_fees_total)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Total Funding</p><p className="font-['JetBrains_Mono'] font-bold text-[#C24A3B]">{fmt(g.total_funding_required)}</p></div>
                </div>

                {/* Provider Breakdown */}
                {g.providers?.length > 0 && (
                  <div className="bg-[#F7F7F4] rounded-xl p-4 border border-[#E2E2DF]">
                    <p className="text-[10px] text-[#8A8A85] uppercase mb-2">Provider Payment Schedule</p>
                    <div className="space-y-1.5">
                      {g.providers.map((p, i) => (
                        <div key={i} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-[#E2E2DF]">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-[#4A6FA5] text-white border-0 text-[9px] font-['JetBrains_Mono']">{p.provider_npi}</Badge>
                            <span className="text-xs text-[#1C1C1A]">{p.provider_name || p.provider_npi}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="text-[10px] text-[#8A8A85]">{p.claim_count} claims</span>
                            <span className="font-['JetBrains_Mono'] text-sm font-semibold text-[#4B6E4E] tabular-nums">{fmt(p.total_payable)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Vendor Fees for this group */}
                {g.vendor_fees?.length > 0 && (
                  <div className="bg-[#F9F5FF] rounded-xl p-4 border border-[#D8C8E8] mt-3">
                    <p className="text-[10px] text-[#8A8A85] uppercase mb-2">Vendor Fee Line Items</p>
                    <div className="space-y-1.5">
                      {g.vendor_fees.map((vf, i) => (
                        <div key={i} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-[#E2E2DF]">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-[#5C2D91] text-white border-0 text-[9px]">{feeTypeLabel(vf.fee_type)}</Badge>
                            <span className="text-xs">{vf.vendor_name}</span>
                            {vf.description && <span className="text-[10px] text-[#8A8A85]">— {vf.description}</span>}
                          </div>
                          <span className="font-['JetBrains_Mono'] text-sm font-semibold text-[#5C2D91] tabular-nums">{fmt(vf.amount)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </TabsContent>

        {/* ═══ RUN HISTORY TAB ═══ */}
        <TabsContent value="history" className="mt-4">
          <div className="container-card p-0 overflow-hidden">
            <div className="p-5 pb-3 flex items-center gap-3">
              <div className="w-10 h-10 bg-[#EDF2EE] rounded-lg flex items-center justify-center"><CreditCard className="h-5 w-5 text-[#4B6E4E]" /></div>
              <div>
                <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Check Run History</h2>
                <p className="text-xs text-[#8A8A85]">Funding requests, WF transfers, ACH batch executions</p>
              </div>
            </div>
            {runs.length === 0 ? (
              <div className="px-5 pb-5"><div className="bg-[#F7F7F4] rounded-lg p-8 text-center"><CreditCard className="h-8 w-8 text-[#E2E2DF] mx-auto mb-2" /><p className="text-sm text-[#8A8A85]">No check runs yet</p></div></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="table-header">
                  <TableHead>Date</TableHead><TableHead>Group</TableHead><TableHead>Period</TableHead><TableHead className="text-right">Claims</TableHead><TableHead className="text-right">Payable</TableHead><TableHead className="text-right">Vendor Fees</TableHead><TableHead className="text-right">Total</TableHead><TableHead>WF Txn</TableHead><TableHead>Status</TableHead><TableHead className="w-[200px]"></TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {runs.map((r) => (
                    <TableRow key={r.id} className="table-row h-[52px] cursor-pointer hover:bg-[#F7F7F4]" onClick={() => openDetail(r.id)} data-testid={`run-row-${r.id}`}>
                      <TableCell className="text-xs tabular-nums text-[#8A8A85]">{new Date(r.created_at).toLocaleDateString()}</TableCell>
                      <TableCell className="text-sm font-medium">{r.group_name}</TableCell>
                      <TableCell className="text-xs text-[#8A8A85]">{r.period_from} — {r.period_to}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{r.claim_count}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold text-[#4B6E4E] tabular-nums">{fmt(r.total_payable)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#5C2D91] tabular-nums">{fmt(r.vendor_fees_total)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-bold tabular-nums">{fmt(r.total_funding_required || r.total_payable)}</TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-[10px]">{r.wf_funding_txn ? <Badge className="bg-[#EFF4FB] text-[#4A6FA5] border-0 text-[9px] font-['JetBrains_Mono']">{r.wf_funding_txn}</Badge> : '—'}</TableCell>
                      <TableCell><Badge className={`${statusColor(r.status)} border-0 text-[10px]`}>{r.status.replace(/_/g, ' ')}</Badge></TableCell>
                      <TableCell className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button variant="outline" size="sm" onClick={() => downloadPdf(r.id)} className="h-7 text-[10px] px-2" title="Download PDF" data-testid={`pdf-${r.id}`}>
                          <FileDown className="h-3 w-3" />
                        </Button>
                        {r.status === 'pending_funding' && (
                          <Button size="sm" onClick={() => confirmFunding(r.id)} className="bg-[#4A6FA5] hover:bg-[#3b5a8a] text-white h-7 text-[10px] px-2" data-testid={`confirm-funding-${r.id}`}>
                            <Landmark className="h-3 w-3 mr-1" />Confirm
                          </Button>
                        )}
                        {r.status === 'funded' && (
                          <Button size="sm" onClick={() => executeRun(r.id)} className="bg-[#4B6E4E] hover:bg-[#3a5a3d] text-white h-7 text-[10px] px-2" data-testid={`execute-run-${r.id}`}>
                            <Play className="h-3 w-3 mr-1" />Execute
                          </Button>
                        )}
                        {r.status === 'executed' && (
                          <Badge className="bg-[#EDF2EE] text-[#4B6E4E] border-0 text-[10px]"><CheckCircle className="h-3 w-3 mr-1" />Settled</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* ═══ VENDOR PAYABLES TAB ═══ */}
        <TabsContent value="vendors" className="mt-4 space-y-4">
          <div className="container-card">
            <div className="mb-5">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Vendor Payables Ledger</h2>
              <p className="text-xs text-[#8A8A85] mt-1">Non-claim vendor fees (PBM access, Telehealth PEPM, etc.) included as line items in weekly ASO check runs.</p>
            </div>

            <div className="bg-[#F7F7F4] rounded-xl p-4 mb-5 border border-[#E2E2DF]" data-testid="vendor-payable-form">
              <p className="text-xs font-medium text-[#64645F] mb-3">Add Vendor Fee</p>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-[10px]">ASO Group</Label>
                  <Select value={vpForm.group_id || 'none'} onValueChange={(v) => setVpForm({...vpForm, group_id: v === 'none' ? '' : v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="vp-group"><SelectValue placeholder="Select..." /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Select Group</SelectItem>
                      {asoGroups.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Vendor Name</Label>
                  <Input value={vpForm.vendor_name} onChange={(e) => setVpForm({...vpForm, vendor_name: e.target.value})} placeholder="e.g. OptumRx" className="input-field h-8 text-xs" data-testid="vp-vendor-name" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Fee Type</Label>
                  <Select value={vpForm.fee_type} onValueChange={(v) => setVpForm({...vpForm, fee_type: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="vp-fee-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pbm_access">PBM Access</SelectItem>
                      <SelectItem value="telehealth_pepm">Telehealth PEPM</SelectItem>
                      <SelectItem value="network_access">Network Access</SelectItem>
                      <SelectItem value="admin_fee">Admin Fee</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Description</Label>
                  <Input value={vpForm.description} onChange={(e) => setVpForm({...vpForm, description: e.target.value})} placeholder="Monthly PBM fee" className="input-field h-8 text-xs" data-testid="vp-description" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Amount ($)</Label>
                  <Input type="number" value={vpForm.amount} onChange={(e) => setVpForm({...vpForm, amount: parseFloat(e.target.value) || 0})} className="input-field h-8 text-xs" data-testid="vp-amount" />
                </div>
                <Button onClick={createVP} disabled={vpSaving} size="sm" className="btn-primary h-8 text-xs" data-testid="vp-create-btn">
                  {vpSaving ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Plus className="h-3 w-3 mr-1" />}Add Fee
                </Button>
              </div>
            </div>

            {vendorPayables.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">No vendor fees configured. Add one above.</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]">
                  <TableHead>Vendor</TableHead><TableHead>Group</TableHead><TableHead>Fee Type</TableHead><TableHead>Description</TableHead><TableHead>Frequency</TableHead><TableHead className="text-right">Amount</TableHead><TableHead>Status</TableHead><TableHead className="w-[60px]"></TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {vendorPayables.map((vp) => (
                    <TableRow key={vp.id} className="table-row h-[48px]" data-testid={`vp-row-${vp.id}`}>
                      <TableCell className="text-sm font-medium">{vp.vendor_name}</TableCell>
                      <TableCell className="text-xs">{asoGroups.find(g => g.id === vp.group_id)?.name || vp.group_id?.slice(0, 8)}</TableCell>
                      <TableCell><Badge className="bg-[#5C2D91] text-white border-0 text-[10px]">{feeTypeLabel(vp.fee_type)}</Badge></TableCell>
                      <TableCell className="text-xs text-[#8A8A85]">{vp.description || '—'}</TableCell>
                      <TableCell className="text-xs capitalize">{vp.frequency}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold tabular-nums">{fmt(vp.amount)}</TableCell>
                      <TableCell><Badge className={vp.is_active ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : 'bg-[#8A8A85] text-white border-0 text-[9px]'}>{vp.is_active ? 'Active' : 'Inactive'}</Badge></TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => deleteVP(vp.id)} className="h-7 w-7 p-0 text-[#C24A3B]" data-testid={`delete-vp-${vp.id}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          {/* WF Integration Reference */}
          <div className="container-card">
            <h3 className="text-sm font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Wells Fargo Settlement Flow</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
              <div className="bg-[#FDF3E1] rounded-lg p-4 border border-[#F5D88E]">
                <div className="flex items-center gap-2 mb-2"><FileText className="h-4 w-4 text-[#C9862B]" /><p className="font-medium text-[#C9862B]">1. Generate Request</p></div>
                <p className="text-[#64645F]">Approved claims are batched by provider. Vendor fees are appended. WF funding pull is initiated.</p>
              </div>
              <div className="bg-[#EFF4FB] rounded-lg p-4 border border-[#C8D8EE]">
                <div className="flex items-center gap-2 mb-2"><Landmark className="h-4 w-4 text-[#4A6FA5]" /><p className="font-medium text-[#4A6FA5]">2. Confirm Funding</p></div>
                <p className="text-[#64645F]">WF webhook confirms the employer debit completed. Funding status moves to 'Funded'.</p>
              </div>
              <div className="bg-[#EDF2EE] rounded-lg p-4 border border-[#D4E5D6]">
                <div className="flex items-center gap-2 mb-2"><Play className="h-4 w-4 text-[#4B6E4E]" /><p className="font-medium text-[#4B6E4E]">3. Execute Run</p></div>
                <p className="text-[#64645F]">WF ACH disbursement pushes payments to each provider. Claims move to 'Paid'.</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4 border border-[#E2E2DF]">
                <div className="flex items-center gap-2 mb-2"><CheckCircle className="h-4 w-4 text-[#64645F]" /><p className="font-medium text-[#64645F]">4. Settled</p></div>
                <p className="text-[#64645F]">WF Transaction IDs recorded on each claim. Visible in Member 360 View.</p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 text-[10px] text-[#8A8A85]">
              <Badge className="bg-[#FDF3E1] text-[#C9862B] border-0 text-[9px]">SIMULATED</Badge>
              Wells Fargo API running in simulation mode. Connect real credentials in Settings for production settlement.
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* ═══ CHECK RUN DETAIL DIALOG ═══ */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          {runDetail && (
            <>
              <DialogHeader>
                <DialogTitle className="font-['Outfit']">Check Run — {runDetail.group_name}</DialogTitle>
                <DialogDescription>
                  Created {new Date(runDetail.created_at).toLocaleString()} | Period: {runDetail.period_from} to {runDetail.period_to}
                </DialogDescription>
              </DialogHeader>

              {/* Summary */}
              <div className="grid grid-cols-4 gap-3 mt-4">
                <div className="bg-[#F7F7F4] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Claims Payable</p>
                  <p className="text-lg font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(runDetail.total_payable)}</p>
                </div>
                <div className="bg-[#F9F5FF] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Vendor Fees</p>
                  <p className="text-lg font-semibold font-['JetBrains_Mono'] text-[#5C2D91]">{fmt(runDetail.vendor_fees_total)}</p>
                </div>
                <div className="bg-[#F7F7F4] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Total Funding</p>
                  <p className="text-lg font-bold font-['JetBrains_Mono']">{fmt(runDetail.total_funding_required || runDetail.total_payable)}</p>
                </div>
                <div className="bg-[#F7F7F4] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Status</p>
                  <Badge className={`${statusColor(runDetail.status)} border-0 text-xs mt-1`}>{runDetail.status.replace(/_/g, ' ')}</Badge>
                </div>
              </div>

              {/* WF Transaction Info */}
              {runDetail.wf_funding_txn && (
                <div className="bg-[#EFF4FB] rounded-lg p-3 mt-3 border border-[#C8D8EE]">
                  <p className="text-[10px] text-[#8A8A85] uppercase mb-1">Wells Fargo Settlement</p>
                  <div className="flex items-center gap-4 text-sm">
                    <div><span className="text-[#8A8A85] text-xs mr-2">Funding Pull:</span><span className="font-['JetBrains_Mono'] font-medium">{runDetail.wf_funding_txn}</span></div>
                    {runDetail.wf_disbursement_id && (
                      <div><span className="text-[#8A8A85] text-xs mr-2">Disbursement:</span><span className="font-['JetBrains_Mono'] font-medium">{runDetail.wf_disbursement_id}</span></div>
                    )}
                    {runDetail.ach_batch && (
                      <div><span className="text-[#8A8A85] text-xs mr-2">ACH Batch:</span><span className="font-['JetBrains_Mono'] font-medium">{runDetail.ach_batch}</span></div>
                    )}
                  </div>
                </div>
              )}

              {/* WF Transactions table */}
              {runDetail.wf_transactions?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-[#64645F] mb-2">Wells Fargo Transactions</p>
                  <div className="max-h-[200px] overflow-y-auto rounded-lg border border-[#E2E2DF]">
                    <Table>
                      <TableHeader><TableRow className="table-header">
                        <TableHead>Type</TableHead><TableHead>Txn ID</TableHead><TableHead>Recipient</TableHead><TableHead className="text-right">Amount</TableHead><TableHead>Method</TableHead><TableHead>Status</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {runDetail.wf_transactions.map(t => (
                          <TableRow key={t.transaction_id} className="h-[36px]">
                            <TableCell><Badge className={t.type === 'funding_pull' ? 'bg-[#C9862B] text-white border-0 text-[9px]' : t.type === 'vendor_fee' ? 'bg-[#5C2D91] text-white border-0 text-[9px]' : 'bg-[#4A6FA5] text-white border-0 text-[9px]'}>{t.type.replace(/_/g, ' ')}</Badge></TableCell>
                            <TableCell className="font-['JetBrains_Mono'] text-[10px]">{t.transaction_id}</TableCell>
                            <TableCell className="text-xs">{t.recipient || t.group_name || '—'}</TableCell>
                            <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{fmt(t.amount)}</TableCell>
                            <TableCell className="text-xs">{t.method || 'ACH'}</TableCell>
                            <TableCell><Badge className={t.status === 'completed' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : 'bg-[#C9862B] text-white border-0 text-[9px]'}>{t.status}</Badge></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {/* Provider Batches */}
              {runDetail.provider_batches?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-[#64645F] mb-2">Provider Payment Batches</p>
                  <div className="space-y-1.5">
                    {runDetail.provider_batches.map((pb, i) => (
                      <div key={i} className="flex items-center justify-between bg-[#F7F7F4] rounded-lg px-3 py-2 border border-[#E2E2DF]">
                        <div className="flex items-center gap-2">
                          <Badge className="bg-[#4A6FA5] text-white border-0 text-[9px] font-['JetBrains_Mono']">{pb.provider_npi}</Badge>
                          <span className="text-xs">{pb.provider_name}</span>
                          <span className="text-[10px] text-[#8A8A85]">({pb.claim_count} claims)</span>
                        </div>
                        <span className="font-['JetBrains_Mono'] text-sm font-semibold text-[#4B6E4E] tabular-nums">{fmt(pb.amount)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Claims */}
              {runDetail.claims?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-[#64645F] mb-2">Claims ({runDetail.claims.length})</p>
                  <div className="max-h-[250px] overflow-y-auto rounded-lg border border-[#E2E2DF]">
                    <Table>
                      <TableHeader><TableRow className="table-header">
                        <TableHead>Claim #</TableHead><TableHead>Member</TableHead><TableHead>Provider</TableHead><TableHead className="text-right">Billed</TableHead><TableHead className="text-right">Paid</TableHead><TableHead>WF Txn</TableHead><TableHead>Status</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {runDetail.claims.map(c => (
                          <TableRow key={c.id} className="h-[36px]" data-testid={`detail-claim-${c.id}`}>
                            <TableCell className="font-['JetBrains_Mono'] text-xs">{c.claim_number}</TableCell>
                            <TableCell className="text-xs">{c.member_id}</TableCell>
                            <TableCell className="text-xs">{c.provider_name || c.provider_npi || '—'}</TableCell>
                            <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{fmt(c.total_billed)}</TableCell>
                            <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold text-[#4B6E4E] tabular-nums">{fmt(c.total_paid)}</TableCell>
                            <TableCell className="font-['JetBrains_Mono'] text-[9px]">{c.wf_transaction_id || '—'}</TableCell>
                            <TableCell><Badge className="bg-[#4B6E4E] text-white border-0 text-[9px]">{c.status}</Badge></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              <DialogFooter className="mt-4 flex gap-2">
                <Button variant="outline" onClick={() => downloadPdf(runDetail.id)} className="text-xs" data-testid="detail-pdf-btn">
                  <FileDown className="h-3.5 w-3.5 mr-1.5" />Download PDF
                </Button>
                {runDetail.status === 'pending_funding' && (
                  <Button onClick={() => confirmFunding(runDetail.id)} className="bg-[#4A6FA5] hover:bg-[#3b5a8a] text-white text-xs" data-testid="detail-confirm-funding">
                    <Landmark className="h-3.5 w-3.5 mr-1.5" />Confirm Funding
                  </Button>
                )}
                {runDetail.status === 'funded' && (
                  <Button onClick={() => executeRun(runDetail.id)} className="bg-[#4B6E4E] hover:bg-[#3a5a3d] text-white text-xs" data-testid="detail-execute-run">
                    <Play className="h-3.5 w-3.5 mr-1.5" />Execute Check Run
                  </Button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
