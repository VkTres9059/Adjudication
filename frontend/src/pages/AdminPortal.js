import { useState, useEffect } from 'react';
import { adminAPI, auditAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Shield, Users, Building2, Activity, Search, Plus, RefreshCw,
  Eye, UserPlus, Briefcase, CheckCircle2, Clock, ChevronRight,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const roleBadge = {
  admin: 'bg-[#1A3636] text-white', tpa_admin: 'bg-[#4A6FA5] text-white',
  mgu_admin: 'bg-[#5C2D91] text-white', carrier_viewer: 'bg-[#C9862B] text-white',
  analytics_viewer: 'bg-[#4B6E4E] text-white',
};

export default function AdminPortal() {
  const [tab, setTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [tpas, setTpas] = useState([]);
  const [auditLogs, setAuditLogs] = useState({ logs: [], total: 0 });
  const [auditSummary, setAuditSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  // New user form
  const [newUser, setNewUser] = useState({ email: '', password: '', name: '', role: 'reviewer', portal_role: 'analytics_viewer' });
  // New TPA form
  const [newTpa, setNewTpa] = useState({ name: '', tax_id: '', contact_name: '', contact_email: '', data_feed_type: 'edi_834_837' });
  // Traceability
  const [traceClaimId, setTraceClaimId] = useState('');
  const [traceResult, setTraceResult] = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [ovRes, usRes, tpaRes, audRes, audSumRes] = await Promise.all([
        adminAPI.systemOverview(),
        adminAPI.users(),
        adminAPI.tpas(),
        auditAPI.logs({ limit: 20 }),
        auditAPI.summary(),
      ]);
      setOverview(ovRes.data);
      setUsers(usRes.data);
      setTpas(tpaRes.data);
      setAuditLogs(audRes.data);
      setAuditSummary(audSumRes.data);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { fetchAll(); }, []);

  const createUser = async () => {
    if (!newUser.email || !newUser.password || !newUser.name) return toast.error('All fields required');
    try {
      await adminAPI.createUser(newUser);
      toast.success('User created');
      setNewUser({ email: '', password: '', name: '', role: 'reviewer', portal_role: 'analytics_viewer' });
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const onboardTpa = async () => {
    if (!newTpa.name || !newTpa.tax_id || !newTpa.contact_name || !newTpa.contact_email) return toast.error('All fields required');
    try {
      await adminAPI.onboardTpa(newTpa);
      toast.success('TPA onboarded');
      setNewTpa({ name: '', tax_id: '', contact_name: '', contact_email: '', data_feed_type: 'edi_834_837' });
      fetchAll();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const runTrace = async () => {
    if (!traceClaimId) return;
    try {
      const res = await adminAPI.traceability(traceClaimId);
      setTraceResult(res.data);
    } catch { toast.error('Claim not found'); setTraceResult(null); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>;

  return (
    <div className="space-y-6" data-testid="admin-portal-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">Admin Portal</h1>
          <p className="text-sm text-[#64645F]">Central control — users, TPAs, audit, and system traceability</p>
        </div>
        <Button variant="outline" onClick={fetchAll} className="text-xs"><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
      </div>

      {/* System Overview Cards */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3" data-testid="admin-overview">
          {[
            { label: 'Users', value: overview.users?.total, icon: Users },
            { label: 'Groups', value: overview.groups, icon: Building2 },
            { label: 'Plans', value: overview.plans, icon: Shield },
            { label: 'Members', value: overview.members, icon: Users },
            { label: 'Claims', value: overview.claims, icon: Activity },
            { label: 'TPAs', value: overview.tpas, icon: Briefcase },
            { label: 'Payments', value: overview.payments, icon: CheckCircle2 },
          ].map(item => (
            <div key={item.label} className="bg-[#F7F7F4] rounded-xl p-3 border border-[#E2E2DF]">
              <div className="flex items-center gap-2 mb-1">
                <item.icon className="h-3.5 w-3.5 text-[#8A8A85]" />
                <p className="text-[10px] text-[#8A8A85]">{item.label}</p>
              </div>
              <p className="text-xl font-semibold font-['Outfit'] text-[#1C1C1A]">{item.value}</p>
            </div>
          ))}
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-[#F0F0EA] p-1 rounded-xl">
          <TabsTrigger value="overview" className="data-[state=active]:bg-white text-sm" data-testid="tab-users"><Users className="h-3.5 w-3.5 mr-1" />Users</TabsTrigger>
          <TabsTrigger value="tpas" className="data-[state=active]:bg-white text-sm" data-testid="tab-tpas"><Briefcase className="h-3.5 w-3.5 mr-1" />TPAs</TabsTrigger>
          <TabsTrigger value="audit" className="data-[state=active]:bg-white text-sm" data-testid="tab-audit"><Clock className="h-3.5 w-3.5 mr-1" />Audit Log</TabsTrigger>
          <TabsTrigger value="trace" className="data-[state=active]:bg-white text-sm" data-testid="tab-trace"><Eye className="h-3.5 w-3.5 mr-1" />Traceability</TabsTrigger>
        </TabsList>

        {/* Users */}
        <TabsContent value="overview" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-4 container-card" data-testid="create-user-form">
              <h3 className="text-base font-medium text-[#1C1C1A] font-['Outfit'] mb-3">Create User</h3>
              <div className="space-y-2">
                <Input value={newUser.name} onChange={e => setNewUser(p => ({ ...p, name: e.target.value }))} placeholder="Full Name" className="input-field text-xs" data-testid="new-user-name" />
                <Input value={newUser.email} onChange={e => setNewUser(p => ({ ...p, email: e.target.value }))} placeholder="Email" className="input-field text-xs" data-testid="new-user-email" />
                <Input type="password" value={newUser.password} onChange={e => setNewUser(p => ({ ...p, password: e.target.value }))} placeholder="Password" className="input-field text-xs" data-testid="new-user-password" />
                <Select value={newUser.portal_role} onValueChange={v => setNewUser(p => ({ ...p, portal_role: v }))}>
                  <SelectTrigger className="input-field text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">System Admin</SelectItem>
                    <SelectItem value="tpa_admin">TPA Admin</SelectItem>
                    <SelectItem value="mgu_admin">MGU Admin</SelectItem>
                    <SelectItem value="carrier_viewer">Carrier Viewer</SelectItem>
                    <SelectItem value="analytics_viewer">Analytics Viewer</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={createUser} className="btn-primary w-full text-xs" data-testid="create-user-btn"><UserPlus className="h-3.5 w-3.5 mr-1" />Create</Button>
              </div>
            </div>
            <div className="col-span-8 container-card p-0 overflow-hidden" data-testid="users-table">
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Portal</TableHead><TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map(u => (
                    <TableRow key={u.id} className="table-row">
                      <TableCell className="text-sm font-medium">{u.name}</TableCell>
                      <TableCell className="text-xs text-[#64645F]">{u.email}</TableCell>
                      <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]">{u.role}</Badge></TableCell>
                      <TableCell><Badge className={`border-0 text-[10px] ${roleBadge[u.portal_role] || 'bg-[#F0F0EA] text-[#64645F]'}`}>{u.portal_role || 'N/A'}</Badge></TableCell>
                      <TableCell><Badge className={`border-0 text-[10px] ${u.active !== false ? 'bg-[#4B6E4E] text-white' : 'bg-[#C24A3B] text-white'}`}>{u.active !== false ? 'Active' : 'Inactive'}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </TabsContent>

        {/* TPAs */}
        <TabsContent value="tpas" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-4 container-card" data-testid="onboard-tpa-form">
              <h3 className="text-base font-medium text-[#1C1C1A] font-['Outfit'] mb-3">Onboard TPA</h3>
              <div className="space-y-2">
                <Input value={newTpa.name} onChange={e => setNewTpa(p => ({ ...p, name: e.target.value }))} placeholder="TPA Name" className="input-field text-xs" data-testid="tpa-name" />
                <Input value={newTpa.tax_id} onChange={e => setNewTpa(p => ({ ...p, tax_id: e.target.value }))} placeholder="Tax ID" className="input-field text-xs" data-testid="tpa-tax-id" />
                <Input value={newTpa.contact_name} onChange={e => setNewTpa(p => ({ ...p, contact_name: e.target.value }))} placeholder="Contact Name" className="input-field text-xs" data-testid="tpa-contact" />
                <Input value={newTpa.contact_email} onChange={e => setNewTpa(p => ({ ...p, contact_email: e.target.value }))} placeholder="Contact Email" className="input-field text-xs" data-testid="tpa-email" />
                <Select value={newTpa.data_feed_type} onValueChange={v => setNewTpa(p => ({ ...p, data_feed_type: v }))}>
                  <SelectTrigger className="input-field text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="edi_834_837">EDI 834/837</SelectItem>
                    <SelectItem value="api">API</SelectItem>
                    <SelectItem value="sftp">SFTP</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={onboardTpa} className="btn-primary w-full text-xs" data-testid="onboard-tpa-btn"><Plus className="h-3.5 w-3.5 mr-1" />Onboard</Button>
              </div>
            </div>
            <div className="col-span-8 container-card" data-testid="tpa-list">
              <h3 className="text-base font-medium text-[#1C1C1A] font-['Outfit'] mb-3">Onboarded TPAs</h3>
              {tpas.length === 0 ? (
                <p className="text-sm text-[#8A8A85] text-center py-6">No TPAs onboarded yet</p>
              ) : (
                <div className="space-y-2">
                  {tpas.map(t => (
                    <div key={t.id} className="flex items-center justify-between p-3 bg-[#F7F7F4] rounded-lg border border-[#E2E2DF]">
                      <div>
                        <p className="text-sm font-medium">{t.name}</p>
                        <p className="text-[10px] text-[#8A8A85]">TIN: {t.tax_id} | {t.contact_email} | Feed: {t.data_feed_type}</p>
                      </div>
                      <Badge className="bg-[#4B6E4E] text-white border-0 text-[10px]">{t.status}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Audit */}
        <TabsContent value="audit" className="mt-4">
          <div className="container-card p-0 overflow-hidden" data-testid="audit-logs-table">
            <div className="p-4 border-b border-[#E2E2DF] flex items-center justify-between">
              <div>
                <h3 className="text-base font-medium text-[#1C1C1A] font-['Outfit']">Audit Trail</h3>
                <p className="text-[10px] text-[#8A8A85]">{auditLogs.total} total events</p>
              </div>
              {auditSummary && (
                <div className="flex gap-2">
                  {auditSummary.by_action?.slice(0, 4).map(a => (
                    <Badge key={a.action} className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]">{a.action}: {a.count}</Badge>
                  ))}
                </div>
              )}
            </div>
            <Table>
              <TableHeader>
                <TableRow className="table-header">
                  <TableHead>Action</TableHead><TableHead>User</TableHead><TableHead>Details</TableHead><TableHead>Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.logs?.map(log => (
                  <TableRow key={log.id} className="table-row">
                    <TableCell><Badge className="bg-[#1A3636] text-white border-0 text-[10px]">{log.action}</Badge></TableCell>
                    <TableCell className="text-xs">{log.user_name || log.user_id?.slice(0, 8)}</TableCell>
                    <TableCell className="text-[10px] text-[#64645F] max-w-[300px] truncate">{JSON.stringify(log.details || {}).slice(0, 80)}</TableCell>
                    <TableCell className="text-[10px] text-[#8A8A85]">{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Traceability */}
        <TabsContent value="trace" className="mt-4">
          <div className="container-card" data-testid="traceability-section">
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-3">Lifecycle Traceability</h3>
            <p className="text-xs text-[#8A8A85] mb-4">Plan Design &rarr; Group &rarr; Eligibility &rarr; Claim &rarr; Payment — full chain</p>
            <div className="flex gap-2 mb-4">
              <Input value={traceClaimId} onChange={e => setTraceClaimId(e.target.value)} onKeyDown={e => e.key === 'Enter' && runTrace()}
                placeholder="Enter Claim ID to trace..." className="input-field" data-testid="trace-claim-input" />
              <Button onClick={runTrace} className="btn-primary" data-testid="trace-btn"><Search className="h-4 w-4 mr-1" />Trace</Button>
            </div>
            {traceResult && (
              <div className="space-y-3" data-testid="trace-result">
                {/* Visual chain */}
                <div className="flex items-center gap-2 flex-wrap">
                  {[
                    { label: 'Plan', data: traceResult.plan, color: 'bg-[#1A3636]' },
                    { label: 'Group', data: traceResult.group, color: 'bg-[#4A6FA5]' },
                    { label: 'Member', data: traceResult.member, color: 'bg-[#5C2D91]' },
                    { label: 'Claim', data: traceResult.claim, color: 'bg-[#C9862B]' },
                    { label: 'Payment', data: traceResult.payment, color: 'bg-[#4B6E4E]' },
                  ].map((step, i) => (
                    <div key={step.label} className="flex items-center gap-2">
                      <div className={`${step.color} text-white rounded-lg px-3 py-2`}>
                        <p className="text-[10px] opacity-75">{step.label}</p>
                        <p className="text-xs font-medium">{step.data?.name || step.data?.claim_number || step.data?.member_id || step.data?.id?.slice(0, 8) || 'N/A'}</p>
                      </div>
                      {i < 4 && <ChevronRight className="h-4 w-4 text-[#8A8A85]" />}
                    </div>
                  ))}
                </div>
                {/* Details */}
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mt-4">
                  {traceResult.plan && (
                    <div className="bg-[#F7F7F4] rounded-lg p-3 border border-[#E2E2DF]">
                      <p className="text-[10px] text-[#8A8A85] mb-1">Plan</p>
                      <p className="text-xs font-medium">{traceResult.plan.name}</p>
                      <p className="text-[10px] text-[#64645F]">v{traceResult.plan.version} | {traceResult.plan.plan_type} | {traceResult.plan.network_type}</p>
                    </div>
                  )}
                  {traceResult.group && (
                    <div className="bg-[#F7F7F4] rounded-lg p-3 border border-[#E2E2DF]">
                      <p className="text-[10px] text-[#8A8A85] mb-1">Group</p>
                      <p className="text-xs font-medium">{traceResult.group.name}</p>
                      <p className="text-[10px] text-[#64645F]">{traceResult.group.funding_type}{traceResult.group.block_of_business ? ` | BOB: ${traceResult.group.block_of_business}` : ''}</p>
                    </div>
                  )}
                  {traceResult.member && (
                    <div className="bg-[#F7F7F4] rounded-lg p-3 border border-[#E2E2DF]">
                      <p className="text-[10px] text-[#8A8A85] mb-1">Member</p>
                      <p className="text-xs font-medium">{traceResult.member.name}</p>
                      <p className="text-[10px] text-[#64645F]">{traceResult.member.status} | {traceResult.member.enrollment_tier || 'N/A'}</p>
                    </div>
                  )}
                  {traceResult.claim && (
                    <div className="bg-[#F7F7F4] rounded-lg p-3 border border-[#E2E2DF]">
                      <p className="text-[10px] text-[#8A8A85] mb-1">Claim</p>
                      <p className="text-xs font-medium">{traceResult.claim.claim_number}</p>
                      <p className="text-[10px] text-[#64645F]">{traceResult.claim.status} | ${traceResult.claim.total_paid?.toFixed(2)}</p>
                    </div>
                  )}
                  {traceResult.payment && (
                    <div className="bg-[#F7F7F4] rounded-lg p-3 border border-[#E2E2DF]">
                      <p className="text-[10px] text-[#8A8A85] mb-1">Payment</p>
                      <p className="text-xs font-medium">${traceResult.payment.amount?.toFixed(2)}</p>
                      <p className="text-[10px] text-[#64645F]">{traceResult.payment.method} | {traceResult.payment.status}</p>
                    </div>
                  )}
                </div>
                {/* Audit Trail */}
                {traceResult.audit_trail?.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-[#1C1C1A] mb-2">Audit Trail</h4>
                    <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
                      {traceResult.audit_trail.map((a, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px]">
                          <span className="text-[#8A8A85] w-[120px] flex-shrink-0">{a.timestamp ? new Date(a.timestamp).toLocaleString() : ''}</span>
                          <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px] flex-shrink-0">{a.action}</Badge>
                          <span className="text-[#64645F] truncate">{JSON.stringify(a.details || {}).slice(0, 60)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
