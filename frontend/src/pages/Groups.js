import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { plansAPI, groupsAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Building2,
  Plus,
  RefreshCw,
  Users,
  DollarSign,
  Shield,
  Server,
  FileText,
  BarChart3,
  ChevronRight,
  Paperclip,
  X,
  Activity,
  TrendingDown,
  ShieldOff,
  Banknote,
  AlertTriangle,
  CreditCard,
  Wallet,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';

const INITIAL_FORM = {
  name: '', tax_id: '', effective_date: new Date().toISOString().split('T')[0],
  termination_date: '', contact_name: '', contact_email: '', contact_phone: '',
  address: '', city: '', state: '', zip_code: '', sic_code: '', employee_count: 0,
  total_premium: 0, mgu_fees: 0, funding_type: 'aso', claims_fund_monthly: 0,
  stop_loss: { specific_deductible: 0, aggregate_attachment_point: 0, aggregate_factor: 125, contract_period: '12_month', laser_deductibles: [] },
  sftp_config: { host: '', port: 22, username: '', directory: '/', schedule: 'daily', file_types: ['834', '835'], enabled: false },
  plan_ids: [],
};

export default function Groups() {
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [pulse, setPulse] = useState(null);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [showAttach, setShowAttach] = useState(false);
  const [showMEC, setShowMEC] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);
  const [reserveFund, setReserveFund] = useState(null);

  const fetchGroups = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/groups');
      setGroups(res.data);
    } catch { toast.error('Failed to load groups'); }
    finally { setLoading(false); }
  }, []);

  const fetchPlans = useCallback(async () => {
    try {
      const res = await plansAPI.list();
      setPlans(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchGroups(); fetchPlans(); }, [fetchGroups, fetchPlans]);

  const openDetail = async (group) => {
    try {
      const [detailRes, pulseRes] = await Promise.all([
        api.get(`/groups/${group.id}`),
        api.get(`/groups/${group.id}/pulse`),
      ]);
      setSelectedGroup(detailRes.data);
      setPulse(pulseRes.data);
      setReserveFund(null);
      setShowDetail(true);
      // Fetch reserve fund for level_funded groups
      if (detailRes.data.funding_type === 'level_funded') {
        try {
          const rfRes = await groupsAPI.getReserveFund(group.id);
          setReserveFund(rfRes.data);
        } catch { /* ok */ }
      }
    } catch { toast.error('Failed to load group details'); }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post('/groups', form);
      toast.success('Group created');
      setShowCreate(false);
      setForm(INITIAL_FORM);
      fetchGroups();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create group'); }
    finally { setSaving(false); }
  };

  const attachPlan = async (planId) => {
    if (!selectedGroup) return;
    setSaving(true);
    try {
      await api.post(`/groups/${selectedGroup.id}/attach-plan?plan_id=${planId}`);
      toast.success('Plan attached to group');
      setShowAttach(false);
      openDetail(selectedGroup);
      fetchGroups();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to attach plan'); }
    finally { setSaving(false); }
  };

  const createMEC1 = async () => {
    if (!selectedGroup) return;
    setSaving(true);
    try {
      await api.post(`/plans/template/mec-1?group_id=${selectedGroup.id}&plan_name=MEC%201%20-%20Standard`);
      toast.success('MEC 1 plan created and attached');
      setShowMEC(false);
      openDetail(selectedGroup);
      fetchPlans();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create MEC 1 plan'); }
    finally { setSaving(false); }
  };

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0);

  const isMecGroup = pulse?.is_mec === true;

  return (
    <div className="space-y-6" data-testid="groups-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Group Management</h1>
          <p className="text-sm text-[#64645F] mt-1">Create employer groups, attach plans, configure stop-loss and SFTP</p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="new-group-btn">
          <Plus className="h-4 w-4 mr-2" />New Group
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><Building2 className="h-4 w-4 text-[#64645F]" /><span className="metric-label">Total Groups</span></div>
          <p className="metric-value">{groups.length}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><Users className="h-4 w-4 text-[#64645F]" /><span className="metric-label">Total Employees</span></div>
          <p className="metric-value">{groups.reduce((s, g) => s + (g.employee_count || 0), 0).toLocaleString()}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><FileText className="h-4 w-4 text-[#64645F]" /><span className="metric-label">Plans Attached</span></div>
          <p className="metric-value">{groups.reduce((s, g) => s + (g.plan_ids?.length || 0), 0)}</p>
        </div>
      </div>

      <div className="container-card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
        ) : groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Building2 className="h-12 w-12 text-[#E2E2DF] mb-4" />
            <p className="text-[#64645F]">No groups yet</p>
            <p className="text-sm text-[#8A8A85]">Create an employer group to get started</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>Group Name</TableHead>
                <TableHead>Tax ID</TableHead>
                <TableHead>Employees</TableHead>
                <TableHead>Plans</TableHead>
                <TableHead>Funding</TableHead>
                <TableHead>Effective</TableHead>
                <TableHead>SFTP</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map((g) => (
                <TableRow key={g.id} className="table-row hover:bg-[#F7F7F4] transition-colors cursor-pointer" onClick={() => openDetail(g)} data-testid={`group-row-${g.id}`}>
                  <TableCell className="font-medium">{g.name}</TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs">{g.tax_id}</TableCell>
                  <TableCell>{g.employee_count?.toLocaleString()}</TableCell>
                  <TableCell><Badge variant="outline" className="text-xs">{g.plan_ids?.length || 0}</Badge></TableCell>
                  <TableCell><Badge className={
                    g.funding_type === 'aso' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                    g.funding_type === 'level_funded' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                    'bg-[#1A3636] text-white border-0 text-[10px]'
                  }>{g.funding_type === 'aso' ? 'ASO' : g.funding_type === 'level_funded' ? 'Level Funded' : 'Fully Insured'}</Badge></TableCell>
                  <TableCell className="text-xs">{g.effective_date}</TableCell>
                  <TableCell>
                    <Badge className={g.sftp_config?.enabled ? 'badge-approved' : 'bg-[#F0F0EA] text-[#8A8A85] border-0'}>{g.sftp_config?.enabled ? g.sftp_config.schedule : 'Off'}</Badge>
                  </TableCell>
                  <TableCell><Badge className="badge-approved">{g.status}</Badge></TableCell>
                  <TableCell><ChevronRight className="h-4 w-4 text-[#8A8A85]" /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* CREATE GROUP MODAL */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">New Employer Group</DialogTitle>
            <DialogDescription>Create a group and configure stop-loss / SFTP</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <Tabs defaultValue="info" className="mt-2">
              <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF] mb-4">
                <TabsTrigger value="info" className="data-[state=active]:bg-white text-xs">Group Info</TabsTrigger>
                <TabsTrigger value="financials" className="data-[state=active]:bg-white text-xs">Financials</TabsTrigger>
                <TabsTrigger value="stoploss" className="data-[state=active]:bg-white text-xs">Stop-Loss</TabsTrigger>
                <TabsTrigger value="sftp" className="data-[state=active]:bg-white text-xs">SFTP</TabsTrigger>
              </TabsList>

              <TabsContent value="info">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>Group Name *</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-field" required data-testid="group-name" /></div>
                  <div className="space-y-2"><Label>Tax ID *</Label><Input value={form.tax_id} onChange={(e) => setForm({ ...form, tax_id: e.target.value })} className="input-field" placeholder="XX-XXXXXXX" required data-testid="group-tax-id" /></div>
                  <div className="space-y-2"><Label>Effective Date *</Label><Input type="date" value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} className="input-field" required data-testid="group-eff-date" /></div>
                  <div className="space-y-2">
                    <Label>Funding Type *</Label>
                    <Select value={form.funding_type} onValueChange={(v) => setForm({ ...form, funding_type: v })}>
                      <SelectTrigger className="input-field" data-testid="group-funding-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="aso">ASO (Administrative Services Only)</SelectItem>
                        <SelectItem value="level_funded">Level Funded</SelectItem>
                        <SelectItem value="fully_insured">Fully Insured</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2"><Label>Employee Count</Label><Input type="number" value={form.employee_count} onChange={(e) => setForm({ ...form, employee_count: parseInt(e.target.value) || 0 })} className="input-field" data-testid="group-emp-count" /></div>
                  <div className="space-y-2"><Label>Contact Name</Label><Input value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} className="input-field" /></div>
                  <div className="space-y-2"><Label>Contact Email</Label><Input value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} className="input-field" /></div>
                  <div className="space-y-2"><Label>State</Label><Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className="input-field" placeholder="TX" /></div>
                  <div className="space-y-2"><Label>City</Label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="input-field" /></div>
                  <div className="space-y-2"><Label>SIC Code</Label><Input value={form.sic_code} onChange={(e) => setForm({ ...form, sic_code: e.target.value })} className="input-field" placeholder="e.g., 3599" /></div>
                  <div className="space-y-2"><Label>Zip Code</Label><Input value={form.zip_code} onChange={(e) => setForm({ ...form, zip_code: e.target.value })} className="input-field" /></div>
                </div>
              </TabsContent>

              <TabsContent value="financials">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Total Premium ($)</Label>
                    <Input type="number" value={form.total_premium} onChange={(e) => setForm({ ...form, total_premium: parseFloat(e.target.value) || 0 })} className="input-field" data-testid="group-total-premium" />
                    <p className="text-[10px] text-[#8A8A85]">Annual premium collected from employer</p>
                  </div>
                  <div className="space-y-2">
                    <Label>MGU Fees ($)</Label>
                    <Input type="number" value={form.mgu_fees} onChange={(e) => setForm({ ...form, mgu_fees: parseFloat(e.target.value) || 0 })} className="input-field" data-testid="group-mgu-fees" />
                    <p className="text-[10px] text-[#8A8A85]">MGU admin fees and carrier retention</p>
                  </div>
                  {form.funding_type === 'level_funded' && (
                    <div className="space-y-2 col-span-2">
                      <Label>Monthly Claims Fund ($)</Label>
                      <Input type="number" value={form.claims_fund_monthly} onChange={(e) => setForm({ ...form, claims_fund_monthly: parseFloat(e.target.value) || 0 })} className="input-field" data-testid="group-claims-fund" />
                      <p className="text-[10px] text-[#8A8A85]">Fixed monthly amount deposited into the claims reserve bucket</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="stoploss">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>Specific Deductible ($)</Label><Input type="number" value={form.stop_loss.specific_deductible} onChange={(e) => setForm({ ...form, stop_loss: { ...form.stop_loss, specific_deductible: parseFloat(e.target.value) || 0 } })} className="input-field" data-testid="sl-specific" /></div>
                  <div className="space-y-2"><Label>Aggregate Attachment Point ($)</Label><Input type="number" value={form.stop_loss.aggregate_attachment_point} onChange={(e) => setForm({ ...form, stop_loss: { ...form.stop_loss, aggregate_attachment_point: parseFloat(e.target.value) || 0 } })} className="input-field" data-testid="sl-aggregate" /></div>
                  <div className="space-y-2"><Label>Aggregate Factor (%)</Label><Input type="number" value={form.stop_loss.aggregate_factor} onChange={(e) => setForm({ ...form, stop_loss: { ...form.stop_loss, aggregate_factor: parseFloat(e.target.value) || 125 } })} className="input-field" /></div>
                  <div className="space-y-2">
                    <Label>Contract Period</Label>
                    <Select value={form.stop_loss.contract_period} onValueChange={(v) => setForm({ ...form, stop_loss: { ...form.stop_loss, contract_period: v } })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="12_month">12 Month</SelectItem>
                        <SelectItem value="15_month">15 Month Run-in</SelectItem>
                        <SelectItem value="paid_incurred">Paid/Incurred</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="sftp">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>SFTP Host</Label><Input value={form.sftp_config.host} onChange={(e) => setForm({ ...form, sftp_config: { ...form.sftp_config, host: e.target.value } })} className="input-field" placeholder="sftp.example.com" data-testid="sftp-host" /></div>
                  <div className="space-y-2"><Label>Username</Label><Input value={form.sftp_config.username} onChange={(e) => setForm({ ...form, sftp_config: { ...form.sftp_config, username: e.target.value } })} className="input-field" /></div>
                  <div className="space-y-2"><Label>Directory</Label><Input value={form.sftp_config.directory} onChange={(e) => setForm({ ...form, sftp_config: { ...form.sftp_config, directory: e.target.value } })} className="input-field" /></div>
                  <div className="space-y-2">
                    <Label>Schedule</Label>
                    <Select value={form.sftp_config.schedule} onValueChange={(v) => setForm({ ...form, sftp_config: { ...form.sftp_config, schedule: v } })}>
                      <SelectTrigger data-testid="sftp-schedule"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                        <SelectItem value="monthly">Monthly</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2 col-span-2 flex items-center gap-3">
                    <input type="checkbox" id="sftp_enabled" checked={form.sftp_config.enabled} onChange={(e) => setForm({ ...form, sftp_config: { ...form.sftp_config, enabled: e.target.checked } })} className="h-4 w-4" data-testid="sftp-enabled" />
                    <Label htmlFor="sftp_enabled">Enable SFTP Scheduler</Label>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</Button>
              <Button type="submit" disabled={saving} className="btn-primary" data-testid="group-submit">
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Create Group'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* GROUP DETAIL PANEL */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedGroup && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <DialogTitle className="font-['Outfit'] text-xl">{selectedGroup.name}</DialogTitle>
                  {isMecGroup && (
                    <Badge className="bg-[#1A3636] text-white text-[10px] border-0" data-testid="mec-badge">
                      <Shield className="h-3 w-3 mr-1" />MEC 1
                    </Badge>
                  )}
                  <Badge className={
                    selectedGroup.funding_type === 'aso' ? 'bg-[#4A6FA5] text-white text-[10px] border-0' :
                    selectedGroup.funding_type === 'level_funded' ? 'bg-[#5C2D91] text-white text-[10px] border-0' :
                    'bg-[#1A3636] text-white text-[10px] border-0'
                  } data-testid="funding-type-badge">
                    {selectedGroup.funding_type === 'aso' ? 'ASO' : selectedGroup.funding_type === 'level_funded' ? 'Level Funded' : selectedGroup.funding_type === 'fully_insured' ? 'Fully Insured' : 'N/A'}
                  </Badge>
                </div>
                <DialogDescription>Tax ID: {selectedGroup.tax_id} | {selectedGroup.city}{selectedGroup.state && `, ${selectedGroup.state}`}</DialogDescription>
              </DialogHeader>

              {pulse && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                  <div className="bg-[#F7F7F4] rounded-lg p-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#8A8A85] font-medium">Members</p>
                    <p className="text-xl font-semibold text-[#1C1C1A] font-['Outfit']">{pulse.member_count}</p>
                  </div>
                  <div className="bg-[#F7F7F4] rounded-lg p-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#8A8A85] font-medium">Claims</p>
                    <p className="text-xl font-semibold text-[#1C1C1A] font-['Outfit']">{pulse.total_claims}</p>
                  </div>
                  <div className="bg-[#F7F7F4] rounded-lg p-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#8A8A85] font-medium">Total Paid</p>
                    <p className="text-xl font-semibold text-[#4B6E4E] font-['JetBrains_Mono']">{fmt(pulse.total_paid)}</p>
                  </div>
                  <div className="bg-[#F7F7F4] rounded-lg p-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#8A8A85] font-medium">PMPM</p>
                    <p className="text-xl font-semibold text-[#1C1C1A] font-['JetBrains_Mono']">{fmt(pulse.pmpm)}</p>
                  </div>
                </div>
              )}

              {/* MEC Financials Section (replaces Stop-Loss for MEC groups) */}
              {isMecGroup && pulse && (
                <div className="bg-[#F7F7F4] rounded-xl p-5 mt-4" data-testid="mec-financials-section">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Banknote className="h-4 w-4 text-[#4B6E4E]" />
                      <h3 className="font-medium text-[#1C1C1A] font-['Outfit']">MEC Financials</h3>
                    </div>
                    <Badge className="bg-[#E8F0E9] text-[#4B6E4E] border-0 text-[10px]" data-testid="self-insured-badge">
                      <ShieldOff className="h-3 w-3 mr-1" />Self-Insured &mdash; No Stop-Loss Required
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-[#8A8A85] text-xs">Total Premium</p>
                      <p className="font-semibold font-['JetBrains_Mono']" data-testid="mec-total-premium">{fmt(pulse.stop_loss?.total_premium)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">MGU Fees</p>
                      <p className="font-semibold font-['JetBrains_Mono']" data-testid="mec-mgu-fees">{fmt(pulse.stop_loss?.mgu_fees)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">Surplus Bucket</p>
                      <p className="font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]" data-testid="mec-surplus">{fmt(pulse.stop_loss?.surplus_bucket)}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm mt-3 pt-3 border-t border-[#E2E2DF]">
                    <div>
                      <p className="text-[#8A8A85] text-xs">Claims Paid YTD</p>
                      <p className="font-semibold font-['JetBrains_Mono']" data-testid="mec-claims-paid">{fmt(pulse.stop_loss?.total_paid_ytd)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">YTD Utilization</p>
                      <p className="font-semibold font-['JetBrains_Mono'] text-[#8A8A85]" data-testid="mec-utilization">N/A</p>
                    </div>
                  </div>
                  <div className="mt-3 text-[10px] text-[#8A8A85] bg-[#E8F0E9] rounded-md px-3 py-1.5">
                    Surplus = Total Premium - (MGU Fees + Claims Paid)
                  </div>
                </div>
              )}

              {/* Level Funded: Claims Reserve Fund Tracker */}
              {selectedGroup.funding_type === 'level_funded' && reserveFund && (
                <div className="bg-[#F9F5FF] rounded-xl p-5 mt-4 border border-[#D8C8E8]" data-testid="reserve-fund-section">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Wallet className="h-4 w-4 text-[#5C2D91]" />
                      <h3 className="font-medium text-[#1C1C1A] font-['Outfit']">Claims Reserve Fund</h3>
                    </div>
                    {reserveFund.in_deficit && (
                      <Badge className="bg-[#C24A3B] text-white border-0 text-[10px]" data-testid="deficit-alert-badge">
                        <AlertTriangle className="h-3 w-3 mr-1" />Deficit — Stop-Loss Review
                      </Badge>
                    )}
                    {!reserveFund.in_deficit && (
                      <Badge className="bg-[#4B6E4E] text-white border-0 text-[10px]" data-testid="reserve-healthy-badge">Healthy</Badge>
                    )}
                  </div>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-[#8A8A85] text-xs">Monthly Deposit</p>
                      <p className="font-semibold font-['JetBrains_Mono']" data-testid="reserve-monthly">{fmt(reserveFund.claims_fund_monthly)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">Total Deposited</p>
                      <p className="font-semibold font-['JetBrains_Mono']" data-testid="reserve-deposited">{fmt(reserveFund.total_deposited)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">Claims Paid</p>
                      <p className="font-semibold font-['JetBrains_Mono'] text-[#C24A3B]" data-testid="reserve-claims-paid">{fmt(reserveFund.total_claims_paid)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">Balance</p>
                      <p className={`font-semibold font-['JetBrains_Mono'] ${reserveFund.balance >= 0 ? 'text-[#4B6E4E]' : 'text-[#C24A3B]'}`} data-testid="reserve-balance">{fmt(reserveFund.balance)}</p>
                    </div>
                  </div>
                  {/* Utilization bar */}
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-[#8A8A85] mb-1">
                      <span>Reserve Utilization</span>
                      <span>{reserveFund.total_deposited > 0 ? Math.round((reserveFund.total_claims_paid / reserveFund.total_deposited) * 100) : 0}%</span>
                    </div>
                    <div className="w-full h-3 bg-[#E2E2DF] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          reserveFund.total_deposited > 0 && (reserveFund.total_claims_paid / reserveFund.total_deposited) > 0.9 ? 'bg-[#C24A3B]' :
                          reserveFund.total_deposited > 0 && (reserveFund.total_claims_paid / reserveFund.total_deposited) > 0.7 ? 'bg-[#C9862B]' :
                          'bg-[#5C2D91]'
                        }`}
                        style={{ width: `${Math.min(100, reserveFund.total_deposited > 0 ? (reserveFund.total_claims_paid / reserveFund.total_deposited) * 100 : 0)}%` }}
                      />
                    </div>
                  </div>
                  {/* Monthly breakdown */}
                  {reserveFund.monthly_breakdown?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[#D8C8E8]">
                      <p className="text-[10px] text-[#8A8A85] uppercase mb-2">Monthly Breakdown</p>
                      <div className="grid grid-cols-6 gap-1.5">
                        {reserveFund.monthly_breakdown.map(m => (
                          <div key={m.month} className="bg-white rounded-lg p-2 border border-[#E2E2DF] text-center">
                            <p className="text-[9px] text-[#8A8A85] font-medium">{m.month}</p>
                            <p className="text-[10px] font-['JetBrains_Mono'] font-semibold text-[#5C2D91]">{fmt(m.deposited)}</p>
                            <p className="text-[10px] font-['JetBrains_Mono'] text-[#C24A3B]">-{fmt(m.claims_paid)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {reserveFund.needs_stop_loss_review && (
                    <div className="mt-3 bg-[#FBEAE7] rounded-lg p-3 flex items-center gap-2 text-xs text-[#C24A3B]" data-testid="stop-loss-review-alert">
                      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                      Claims have exceeded the funded reserve. This group is flagged for Aggregate Stop-Loss review.
                    </div>
                  )}
                </div>
              )}

              {/* Standard Stop-Loss Section (hidden for MEC groups) */}
              {!isMecGroup && pulse?.stop_loss && pulse.stop_loss.aggregate_attachment_point > 0 && (
                <div className="bg-[#F7F7F4] rounded-xl p-5 mt-4" data-testid="stop-loss-section">
                  <div className="flex items-center gap-2 mb-3"><Shield className="h-4 w-4 text-[#C9862B]" /><h3 className="font-medium text-[#1C1C1A] font-['Outfit']">Stop-Loss Status</h3></div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-[#8A8A85] text-xs">Specific Deductible</p>
                      <p className="font-semibold font-['JetBrains_Mono']">{fmt(pulse.stop_loss.specific_deductible)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">Aggregate Attachment</p>
                      <p className="font-semibold font-['JetBrains_Mono']">{fmt(pulse.stop_loss.aggregate_attachment_point)}</p>
                    </div>
                    <div>
                      <p className="text-[#8A8A85] text-xs">Surplus Bucket</p>
                      <p className="font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(pulse.stop_loss.surplus_bucket)}</p>
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-[#8A8A85] mb-1">
                      <span>YTD Utilization</span>
                      <span>{pulse.stop_loss.utilization_pct}%</span>
                    </div>
                    <div className="w-full h-3 bg-[#E2E2DF] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${pulse.stop_loss.utilization_pct > 80 ? 'bg-[#C24A3B]' : pulse.stop_loss.utilization_pct > 50 ? 'bg-[#C9862B]' : 'bg-[#4B6E4E]'}`} style={{ width: `${Math.min(100, pulse.stop_loss.utilization_pct)}%` }} />
                    </div>
                  </div>
                </div>
              )}

              {/* SFTP Config */}
              {selectedGroup.sftp_config?.enabled && (
                <div className="bg-[#F7F7F4] rounded-xl p-5 mt-4">
                  <div className="flex items-center gap-2 mb-3"><Server className="h-4 w-4 text-[#2563EB]" /><h3 className="font-medium text-[#1C1C1A] font-['Outfit']">SFTP Scheduler</h3></div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div><p className="text-[#8A8A85] text-xs">Host</p><p className="font-['JetBrains_Mono'] text-xs">{selectedGroup.sftp_config.host || 'Not set'}</p></div>
                    <div><p className="text-[#8A8A85] text-xs">Schedule</p><p className="capitalize">{selectedGroup.sftp_config.schedule}</p></div>
                    <div><p className="text-[#8A8A85] text-xs">File Types</p><p>{selectedGroup.sftp_config.file_types?.join(', ')}</p></div>
                  </div>
                </div>
              )}

              {/* Attached Plans */}
              <div className="mt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-[#1C1C1A] font-['Outfit']">Plan Offerings</h3>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setShowMEC(true)} className="btn-secondary text-xs" data-testid="create-mec1-btn">
                      <Shield className="h-3 w-3 mr-1" />MEC 1 Template
                    </Button>
                    <Button size="sm" onClick={() => setShowAttach(true)} className="btn-primary text-xs" data-testid="attach-plan-btn">
                      <Paperclip className="h-3 w-3 mr-1" />Attach Plan
                    </Button>
                  </div>
                </div>
                {selectedGroup.attached_plans?.length === 0 ? (
                  <div className="bg-[#F7F7F4] rounded-lg p-8 text-center">
                    <FileText className="h-8 w-8 text-[#E2E2DF] mx-auto mb-2" />
                    <p className="text-sm text-[#8A8A85]">No plans attached</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {selectedGroup.attached_plans?.map((plan) => (
                      <div key={plan.id} className="bg-[#F7F7F4] rounded-lg p-4 flex items-center justify-between" data-testid={`plan-card-${plan.id}`}>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-sm">{plan.name}</p>
                            {plan.plan_template === 'mec_1' && <Badge className="badge-approved text-[10px]">MEC 1</Badge>}
                            {plan.plan_template === 'mec_1' && (
                              <Badge className="bg-[#E8F0E9] text-[#4B6E4E] border-0 text-[10px]" data-testid="no-stop-loss-badge">
                                <ShieldOff className="h-2.5 w-2.5 mr-0.5" />No Stop-Loss
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-[#8A8A85] mt-0.5">
                            {plan.plan_type} | {plan.network_type} | Preventive: {plan.preventive_design === 'aca_strict' ? 'ACA Strict' : 'Enhanced'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-[#8A8A85]">Deductible</p>
                          <p className="font-['JetBrains_Mono'] text-xs font-semibold">{fmt(plan.deductible_individual)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* ATTACH PLAN MODAL */}
      <Dialog open={showAttach} onOpenChange={setShowAttach}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Attach Plan</DialogTitle>
            <DialogDescription>Select a plan to attach to {selectedGroup?.name}</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-4 max-h-[300px] overflow-y-auto">
            {plans.filter(p => !selectedGroup?.plan_ids?.includes(p.id)).map((plan) => (
              <button key={plan.id} onClick={() => attachPlan(plan.id)} className="w-full text-left bg-[#F7F7F4] hover:bg-[#E2E2DF] rounded-lg p-4 transition-colors" data-testid={`attach-${plan.id}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{plan.name}</p>
                    <p className="text-xs text-[#8A8A85]">{plan.plan_type} | {plan.network_type}</p>
                  </div>
                  <Paperclip className="h-4 w-4 text-[#8A8A85]" />
                </div>
              </button>
            ))}
            {plans.filter(p => !selectedGroup?.plan_ids?.includes(p.id)).length === 0 && (
              <p className="text-center text-sm text-[#8A8A85] py-8">All plans are already attached or no plans exist</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* MEC 1 CONFIRMATION */}
      <Dialog open={showMEC} onOpenChange={setShowMEC}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Create MEC 1 Plan</DialogTitle>
            <DialogDescription>This will create a Minimum Essential Coverage plan with ACA-compliant preventive services only and attach it to {selectedGroup?.name}.</DialogDescription>
          </DialogHeader>
          <div className="bg-[#F7F7F4] rounded-lg p-4 space-y-2 text-sm my-4">
            <div className="flex justify-between"><span className="text-[#64645F]">Plan Name</span><span className="font-medium">MEC 1 - Standard</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">Deductible</span><span className="font-['JetBrains_Mono'] text-xs">$0</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">OOP Max</span><span className="font-['JetBrains_Mono'] text-xs">$0</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">Preventive Design</span><span>ACA Strict</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">Covered Benefits</span><span>10 preventive categories</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">Exclusions</span><span>30 service categories</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">Pre-auth Penalty</span><span>50%</span></div>
            <div className="flex justify-between"><span className="text-[#64645F]">Non-network</span><span>Reference-based pricing</span></div>
            <div className="flex justify-between border-t border-[#E2E2DF] pt-2 mt-2">
              <span className="text-[#64645F]">Stop-Loss</span>
              <Badge className="bg-[#E8F0E9] text-[#4B6E4E] border-0 text-[10px]">
                <ShieldOff className="h-2.5 w-2.5 mr-0.5" />Not Required (Self-Insured)
              </Badge>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMEC(false)} className="btn-secondary">Cancel</Button>
            <Button onClick={createMEC1} disabled={saving} className="btn-primary" data-testid="confirm-mec1">
              {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Create MEC 1 Plan'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
