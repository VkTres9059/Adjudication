import { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { checkRunAPI } from '../lib/api';
import {
  DollarSign,
  RefreshCw,
  FileText,
  Building2,
  Play,
  CheckCircle,
  Clock,
  AlertTriangle,
  ArrowRight,
  Download,
  Users,
  Banknote,
  CreditCard,
} from 'lucide-react';

export default function CheckRunManager() {
  const [asoGroups, setAsoGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('');
  const [pending, setPending] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [runDetail, setRunDetail] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [groupsRes, pendingRes, runsRes] = await Promise.all([
        checkRunAPI.getAsoGroups(),
        checkRunAPI.getPending(selectedGroup || undefined),
        checkRunAPI.list(selectedGroup || undefined),
      ]);
      setAsoGroups(groupsRes.data);
      setPending(pendingRes.data);
      setRuns(runsRes.data);
    } catch { toast.error('Failed to load check run data'); }
    finally { setLoading(false); }
  }, [selectedGroup]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(v || 0);

  const generateRequest = async (groupId) => {
    setGenerating(true);
    try {
      await checkRunAPI.generateFundingRequest(groupId);
      toast.success('Funding request generated');
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to generate funding request'); }
    finally { setGenerating(false); }
  };

  const confirmFunding = async (runId) => {
    try {
      await checkRunAPI.confirmFunding(runId);
      toast.success('Funding confirmed');
      fetchAll();
      if (showDetail) openDetail(runId);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to confirm funding'); }
  };

  const executeRun = async (runId) => {
    try {
      const res = await checkRunAPI.execute(runId);
      toast.success(`Check run executed — ACH Batch: ${res.data.ach_batch}`);
      fetchAll();
      if (showDetail) openDetail(runId);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to execute check run'); }
  };

  const openDetail = async (runId) => {
    try {
      const res = await checkRunAPI.get(runId);
      setRunDetail(res.data);
      setShowDetail(true);
    } catch { toast.error('Failed to load run details'); }
  };

  const totalPending = pending.reduce((s, g) => s + g.provider_payable, 0);
  const totalClaims = pending.reduce((s, g) => s + g.claim_count, 0);

  const statusColor = (s) => {
    switch (s) {
      case 'pending_funding': return 'bg-[#C9862B] text-white';
      case 'funded': return 'bg-[#4A6FA5] text-white';
      case 'executed': return 'bg-[#4B6E4E] text-white';
      default: return 'bg-[#8A8A85] text-white';
    }
  };

  return (
    <div className="space-y-6" data-testid="check-run-manager">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Check Run Manager</h1>
          <p className="text-sm text-[#64645F] mt-1">ASO weekly claim aggregation, funding requests, and check issuance</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedGroup || 'all'} onValueChange={(v) => setSelectedGroup(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-[200px] input-field text-sm" data-testid="group-filter-select">
              <SelectValue placeholder="All ASO Groups" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Groups</SelectItem>
              {asoGroups.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={fetchAll} variant="outline" className="btn-secondary" data-testid="refresh-check-runs">
            <RefreshCw className="h-4 w-4 mr-2" />Refresh
          </Button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card" data-testid="metric-aso-groups">
          <div className="flex items-center gap-2 mb-2"><Building2 className="h-4 w-4 text-[#64645F]" /><span className="metric-label">ASO Groups</span></div>
          <p className="metric-value">{asoGroups.length}</p>
        </div>
        <div className="metric-card" data-testid="metric-pending-claims">
          <div className="flex items-center gap-2 mb-2"><FileText className="h-4 w-4 text-[#C9862B]" /><span className="metric-label">Claims Pending Funding</span></div>
          <p className="metric-value">{totalClaims}</p>
        </div>
        <div className="metric-card" data-testid="metric-pending-amount">
          <div className="flex items-center gap-2 mb-2"><DollarSign className="h-4 w-4 text-[#C24A3B]" /><span className="metric-label">Total Payable</span></div>
          <p className="metric-value font-['JetBrains_Mono']">{fmt(totalPending)}</p>
        </div>
        <div className="metric-card" data-testid="metric-total-runs">
          <div className="flex items-center gap-2 mb-2"><CreditCard className="h-4 w-4 text-[#4B6E4E]" /><span className="metric-label">Check Runs</span></div>
          <p className="metric-value">{runs.length}</p>
        </div>
      </div>

      {/* Pending Claims by Group */}
      <div className="container-card">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 bg-[#FDF3E1] rounded-lg flex items-center justify-center"><Banknote className="h-5 w-5 text-[#C9862B]" /></div>
          <div>
            <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Pending Funding Requests</h2>
            <p className="text-xs text-[#8A8A85]">Approved claims awaiting employer funding. Generate a request to initiate the check run.</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>
        ) : pending.length === 0 ? (
          <div className="bg-[#F7F7F4] rounded-lg p-8 text-center">
            <CheckCircle className="h-8 w-8 text-[#4B6E4E] mx-auto mb-2" />
            <p className="text-sm text-[#8A8A85]">No approved claims pending a check run</p>
          </div>
        ) : (
          <div className="space-y-3">
            {pending.map((g) => (
              <div key={g.group_id} className="bg-[#F7F7F4] rounded-xl p-5 border border-[#E2E2DF]" data-testid={`pending-group-${g.group_id}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Building2 className="h-5 w-5 text-[#1A3636]" />
                    <div>
                      <p className="font-medium text-sm text-[#1C1C1A]">{g.group_name}</p>
                      <p className="text-[10px] text-[#8A8A85]">{g.claim_count} claims | {g.members?.length || 0} members</p>
                    </div>
                  </div>
                  <Button onClick={() => generateRequest(g.group_id)} disabled={generating} className="btn-primary text-xs" data-testid={`gen-funding-${g.group_id}`}>
                    {generating ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <FileText className="h-3 w-3 mr-1" />}
                    Generate Funding Request
                  </Button>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Total Billed</p><p className="font-['JetBrains_Mono'] font-semibold">{fmt(g.total_billed)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Member Resp.</p><p className="font-['JetBrains_Mono'] font-semibold">{fmt(g.member_resp)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Provider Payable</p><p className="font-['JetBrains_Mono'] font-semibold text-[#4B6E4E]">{fmt(g.provider_payable)}</p></div>
                  <div><p className="text-[10px] text-[#8A8A85] uppercase">Claims</p><p className="font-['JetBrains_Mono'] font-semibold">{g.claim_count}</p></div>
                </div>
                {g.members?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#E2E2DF]">
                    <p className="text-[10px] text-[#8A8A85] uppercase mb-2">Members</p>
                    <div className="flex flex-wrap gap-2">
                      {g.members.slice(0, 8).map(m => (
                        <Badge key={m.member_id} className="bg-white text-[#1C1C1A] border border-[#E2E2DF] text-[10px]">
                          {m.name} ({m.claim_count}) — {fmt(m.total_paid)}
                        </Badge>
                      ))}
                      {g.members.length > 8 && <Badge className="bg-[#F0F0EA] text-[#8A8A85] border-0 text-[10px]">+{g.members.length - 8} more</Badge>}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Check Run History */}
      <div className="container-card p-0 overflow-hidden">
        <div className="p-5 pb-3 flex items-center gap-3">
          <div className="w-10 h-10 bg-[#EDF2EE] rounded-lg flex items-center justify-center"><CreditCard className="h-5 w-5 text-[#4B6E4E]" /></div>
          <div>
            <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Check Run History</h2>
            <p className="text-xs text-[#8A8A85]">Track funding requests, confirmations, and ACH batch executions</p>
          </div>
        </div>

        {runs.length === 0 ? (
          <div className="px-5 pb-5"><div className="bg-[#F7F7F4] rounded-lg p-8 text-center"><CreditCard className="h-8 w-8 text-[#E2E2DF] mx-auto mb-2" /><p className="text-sm text-[#8A8A85]">No check runs yet</p></div></div>
        ) : (
          <Table>
            <TableHeader><TableRow className="table-header">
              <TableHead>Date</TableHead><TableHead>Group</TableHead><TableHead>Period</TableHead><TableHead className="text-right">Claims</TableHead><TableHead className="text-right">Payable</TableHead><TableHead>ACH Batch</TableHead><TableHead>Status</TableHead><TableHead className="w-[160px]"></TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {runs.map((r) => (
                <TableRow key={r.id} className="table-row h-[52px] cursor-pointer hover:bg-[#F7F7F4]" onClick={() => openDetail(r.id)} data-testid={`run-row-${r.id}`}>
                  <TableCell className="text-xs tabular-nums text-[#8A8A85]">{new Date(r.created_at).toLocaleDateString()}</TableCell>
                  <TableCell className="text-sm font-medium">{r.group_name}</TableCell>
                  <TableCell className="text-xs text-[#8A8A85]">{r.period_from} — {r.period_to}</TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{r.claim_count}</TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold text-[#4B6E4E] tabular-nums">{fmt(r.total_payable)}</TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs">{r.ach_batch || '—'}</TableCell>
                  <TableCell><Badge className={`${statusColor(r.status)} border-0 text-[10px]`}>{r.status.replace('_', ' ')}</Badge></TableCell>
                  <TableCell className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    {r.status === 'pending_funding' && (
                      <Button size="sm" onClick={() => confirmFunding(r.id)} className="bg-[#4A6FA5] hover:bg-[#3b5a8a] text-white h-7 text-[10px] px-2" data-testid={`confirm-funding-${r.id}`}>
                        <CheckCircle className="h-3 w-3 mr-1" />Confirm Funding
                      </Button>
                    )}
                    {r.status === 'funded' && (
                      <Button size="sm" onClick={() => executeRun(r.id)} className="bg-[#4B6E4E] hover:bg-[#3a5a3d] text-white h-7 text-[10px] px-2" data-testid={`execute-run-${r.id}`}>
                        <Play className="h-3 w-3 mr-1" />Execute Check Run
                      </Button>
                    )}
                    {r.status === 'executed' && (
                      <Badge className="bg-[#EDF2EE] text-[#4B6E4E] border-0 text-[10px]"><CheckCircle className="h-3 w-3 mr-1" />Paid</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Check Run Detail Dialog */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          {runDetail && (
            <>
              <DialogHeader>
                <DialogTitle className="font-['Outfit']">Check Run — {runDetail.group_name}</DialogTitle>
                <DialogDescription>
                  Created {new Date(runDetail.created_at).toLocaleString()} | Period: {runDetail.period_from} to {runDetail.period_to}
                </DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-3 gap-3 mt-4">
                <div className="bg-[#F7F7F4] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Total Payable</p>
                  <p className="text-xl font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(runDetail.total_payable)}</p>
                </div>
                <div className="bg-[#F7F7F4] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Claims</p>
                  <p className="text-xl font-semibold font-['Outfit']">{runDetail.claim_count}</p>
                </div>
                <div className="bg-[#F7F7F4] rounded-lg p-3">
                  <p className="text-[10px] text-[#8A8A85] uppercase">Status</p>
                  <Badge className={`${statusColor(runDetail.status)} border-0 text-xs mt-1`}>{runDetail.status.replace('_', ' ')}</Badge>
                </div>
              </div>
              {runDetail.ach_batch && (
                <div className="bg-[#EDF2EE] rounded-lg p-3 mt-3 flex items-center justify-between">
                  <div><p className="text-[10px] text-[#64645F]">ACH Batch Number</p><p className="font-['JetBrains_Mono'] text-sm font-semibold">{runDetail.ach_batch}</p></div>
                  <Badge className="bg-[#4B6E4E] text-white border-0 text-xs"><CheckCircle className="h-3 w-3 mr-1" />Executed</Badge>
                </div>
              )}
              {runDetail.claims?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-[#64645F] mb-2">Claims in this run</p>
                  <div className="max-h-[300px] overflow-y-auto rounded-lg border border-[#E2E2DF]">
                    <Table>
                      <TableHeader><TableRow className="table-header">
                        <TableHead>Claim #</TableHead><TableHead>Member</TableHead><TableHead className="text-right">Billed</TableHead><TableHead className="text-right">Paid</TableHead><TableHead>Status</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {runDetail.claims.map(c => (
                          <TableRow key={c.id} className="h-[40px]" data-testid={`detail-claim-${c.id}`}>
                            <TableCell className="font-['JetBrains_Mono'] text-xs">{c.claim_number}</TableCell>
                            <TableCell className="text-xs">{c.member_id}</TableCell>
                            <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{fmt(c.total_billed)}</TableCell>
                            <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold text-[#4B6E4E] tabular-nums">{fmt(c.total_paid)}</TableCell>
                            <TableCell><Badge className="bg-[#4B6E4E] text-white border-0 text-[9px]">{c.status}</Badge></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
              <DialogFooter className="mt-4">
                {runDetail.status === 'pending_funding' && (
                  <Button onClick={() => confirmFunding(runDetail.id)} className="bg-[#4A6FA5] hover:bg-[#3b5a8a] text-white" data-testid="detail-confirm-funding">
                    <CheckCircle className="h-4 w-4 mr-2" />Confirm Funding
                  </Button>
                )}
                {runDetail.status === 'funded' && (
                  <Button onClick={() => executeRun(runDetail.id)} className="bg-[#4B6E4E] hover:bg-[#3a5a3d] text-white" data-testid="detail-execute-run">
                    <Play className="h-4 w-4 mr-2" />Execute Check Run
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
