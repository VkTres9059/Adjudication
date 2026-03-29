import { useState, useEffect } from 'react';
import api from '../lib/api';
import { settingsAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Cog,
  Users,
  Shield,
  Save,
  RefreshCw,
  AlertTriangle,
  Zap,
  Search,
  Lock,
  Layers,
  DollarSign,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';

const INITIAL_USER = { name: '', email: '', password: '', role: 'adjudicator' };

export default function Settings() {
  const [users, setUsers] = useState([]);
  const [userForm, setUserForm] = useState(INITIAL_USER);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [gatewayConfig, setGatewayConfig] = useState({
    tier1_auto_pilot_limit: 500,
    tier2_audit_hold_limit: 2500,
    enabled: true,
  });
  const [gatewaySaving, setGatewaySaving] = useState(false);
  const [bridgeConfig, setBridgeConfig] = useState({
    enabled: false,
    rate_per_hour: 20,
  });
  const [bridgeSaving, setBridgeSaving] = useState(false);

  useEffect(() => {
    fetchUsers();
    fetchGatewayConfig();
    fetchBridgeConfig();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/users');
      setUsers(res.data);
    } catch { toast.error('Failed to load users'); }
    finally { setLoading(false); }
  };

  const fetchGatewayConfig = async () => {
    try {
      const res = await settingsAPI.getGateway();
      setGatewayConfig(res.data);
    } catch { /* defaults are fine */ }
  };

  const createUser = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post('/users', userForm);
      toast.success('User created');
      setUserForm(INITIAL_USER);
      fetchUsers();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create user'); }
    finally { setSaving(false); }
  };

  const saveGateway = async () => {
    setGatewaySaving(true);
    try {
      await settingsAPI.updateGateway(gatewayConfig);
      toast.success('Adjudication Gateway updated');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to update gateway'); }
    finally { setGatewaySaving(false); }
  };

  const fetchBridgeConfig = async () => {
    try {
      const res = await settingsAPI.getBridge();
      setBridgeConfig(res.data);
    } catch { /* defaults are fine */ }
  };

  const saveBridge = async () => {
    setBridgeSaving(true);
    try {
      await settingsAPI.updateBridge(bridgeConfig);
      toast.success('Bridge Payment settings updated');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to update bridge settings'); }
    finally { setBridgeSaving(false); }
  };

  const fmt = (v) => `$${Number(v || 0).toLocaleString()}`;

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Settings</h1>
        <p className="text-sm text-[#64645F] mt-1">System configuration, user management, and adjudication gateway</p>
      </div>

      <Tabs defaultValue="gateway" className="w-full">
        <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF]">
          <TabsTrigger value="gateway" className="data-[state=active]:bg-white text-sm" data-testid="tab-gateway"><Layers className="h-3.5 w-3.5 mr-1.5" />Adjudication Gateway</TabsTrigger>
          <TabsTrigger value="bridge" className="data-[state=active]:bg-white text-sm" data-testid="tab-bridge"><DollarSign className="h-3.5 w-3.5 mr-1.5" />Bridge Payments</TabsTrigger>
          <TabsTrigger value="users" className="data-[state=active]:bg-white text-sm" data-testid="tab-users"><Users className="h-3.5 w-3.5 mr-1.5" />Users</TabsTrigger>
          <TabsTrigger value="system" className="data-[state=active]:bg-white text-sm" data-testid="tab-system"><Cog className="h-3.5 w-3.5 mr-1.5" />System</TabsTrigger>
        </TabsList>

        {/* ADJUDICATION GATEWAY TAB */}
        <TabsContent value="gateway" className="mt-6 space-y-6">
          <div className="container-card">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Tiered Authorization Matrix</h2>
                <p className="text-xs text-[#8A8A85] mt-1">Global thresholds that control auto-adjudication behavior across all plan types</p>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={gatewayConfig.enabled}
                    onChange={(e) => setGatewayConfig({ ...gatewayConfig, enabled: e.target.checked })}
                    className="h-4 w-4 rounded"
                    data-testid="gateway-enabled"
                  />
                  <span className="text-sm font-medium text-[#1C1C1A]">Enabled</span>
                </label>
                <Badge className={gatewayConfig.enabled ? 'badge-approved' : 'bg-[#F0F0EA] text-[#8A8A85] border-0'}>
                  {gatewayConfig.enabled ? 'Active' : 'Disabled'}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Tier 1 */}
              <div className={`rounded-xl p-5 border-2 transition-all ${gatewayConfig.enabled ? 'border-[#4B6E4E] bg-[#F7FAF7]' : 'border-[#E2E2DF] bg-[#F7F7F4] opacity-60'}`} data-testid="tier-1-card">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-[#4B6E4E] flex items-center justify-center"><Zap className="h-4 w-4 text-white" /></div>
                  <div>
                    <p className="font-medium text-sm text-[#1C1C1A] font-['Outfit']">Tier 1 — Auto-Pilot</p>
                    <p className="text-[10px] text-[#8A8A85]">Fully automated, no human touch</p>
                  </div>
                </div>
                <div className="space-y-2 mt-4">
                  <Label className="text-xs">Claims up to:</Label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#64645F]">$</span>
                    <Input
                      type="number"
                      value={gatewayConfig.tier1_auto_pilot_limit}
                      onChange={(e) => setGatewayConfig({ ...gatewayConfig, tier1_auto_pilot_limit: parseFloat(e.target.value) || 0 })}
                      className="input-field"
                      disabled={!gatewayConfig.enabled}
                      data-testid="tier1-limit"
                    />
                  </div>
                </div>
                <div className="mt-4 text-xs text-[#64645F] bg-white rounded-md p-2.5 border border-[#E2E2DF]">
                  Claims ≤ {fmt(gatewayConfig.tier1_auto_pilot_limit)} that match Code DB + Census → <span className="font-semibold text-[#4B6E4E]">Auto-Paid</span>
                </div>
              </div>

              {/* Tier 2 */}
              <div className={`rounded-xl p-5 border-2 transition-all ${gatewayConfig.enabled ? 'border-[#C9862B] bg-[#FFFBF5]' : 'border-[#E2E2DF] bg-[#F7F7F4] opacity-60'}`} data-testid="tier-2-card">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-[#C9862B] flex items-center justify-center"><Search className="h-4 w-4 text-white" /></div>
                  <div>
                    <p className="font-medium text-sm text-[#1C1C1A] font-['Outfit']">Tier 2 — Audit Hold</p>
                    <p className="text-[10px] text-[#8A8A85]">Auto-adjudicated, flagged for audit</p>
                  </div>
                </div>
                <div className="space-y-2 mt-4">
                  <Label className="text-xs">Claims up to:</Label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#64645F]">$</span>
                    <Input
                      type="number"
                      value={gatewayConfig.tier2_audit_hold_limit}
                      onChange={(e) => setGatewayConfig({ ...gatewayConfig, tier2_audit_hold_limit: parseFloat(e.target.value) || 0 })}
                      className="input-field"
                      disabled={!gatewayConfig.enabled}
                      data-testid="tier2-limit"
                    />
                  </div>
                </div>
                <div className="mt-4 text-xs text-[#64645F] bg-white rounded-md p-2.5 border border-[#E2E2DF]">
                  Claims {fmt(gatewayConfig.tier1_auto_pilot_limit)}–{fmt(gatewayConfig.tier2_audit_hold_limit)} → <span className="font-semibold text-[#C9862B]">Paid + Post-Payment Audit</span>
                </div>
              </div>

              {/* Tier 3 */}
              <div className={`rounded-xl p-5 border-2 transition-all ${gatewayConfig.enabled ? 'border-[#C24A3B] bg-[#FFF5F5]' : 'border-[#E2E2DF] bg-[#F7F7F4] opacity-60'}`} data-testid="tier-3-card">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-[#C24A3B] flex items-center justify-center"><Lock className="h-4 w-4 text-white" /></div>
                  <div>
                    <p className="font-medium text-sm text-[#1C1C1A] font-['Outfit']">Tier 3 — Hard Hold</p>
                    <p className="text-[10px] text-[#8A8A85]">Requires examiner digital signature</p>
                  </div>
                </div>
                <div className="space-y-2 mt-4">
                  <Label className="text-xs">Claims above Tier 2 limit</Label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#64645F]">$</span>
                    <Input
                      value={gatewayConfig.tier2_audit_hold_limit}
                      className="input-field bg-[#F7F7F4]"
                      disabled
                    />
                    <span className="text-xs text-[#8A8A85]">+</span>
                  </div>
                </div>
                <div className="mt-4 text-xs text-[#64645F] bg-white rounded-md p-2.5 border border-[#E2E2DF]">
                  Claims &gt; {fmt(gatewayConfig.tier2_audit_hold_limit)} → <span className="font-semibold text-[#C24A3B]">Pending Review (Hard Hold)</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between mt-6 pt-4 border-t border-[#E2E2DF]">
              <div className="flex items-center gap-2 text-xs text-[#8A8A85]">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Changes apply to all future claims immediately. Existing claims are not retroactively re-tiered.</span>
              </div>
              <Button onClick={saveGateway} disabled={gatewaySaving} className="btn-primary" data-testid="save-gateway-btn">
                {gatewaySaving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                Save Gateway Config
              </Button>
            </div>
          </div>

          {/* How It Works */}
          <div className="container-card">
            <h3 className="text-sm font-medium text-[#1C1C1A] font-['Outfit'] mb-4">How the Gateway Protects Your MGU</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="bg-[#F7FAF7] rounded-lg p-4 border border-[#D4E5D6]">
                <p className="font-medium text-[#4B6E4E] mb-1">Auto-Adjudication Leakage Prevention</p>
                <p className="text-[#64645F]">A $100k trauma claim on a standard plan won't auto-process — Tier 3 catches it and holds for examiner verification of Stop-Loss coordinates.</p>
              </div>
              <div className="bg-[#FFFBF5] rounded-lg p-4 border border-[#E8D5B5]">
                <p className="font-medium text-[#C9862B] mb-1">Post-Payment Audit Trail</p>
                <p className="text-[#64645F]">Mid-range claims are paid fast but logged for audit. Carriers see clean Bordereaux with audit-flagged claims marked for review.</p>
              </div>
              <div className="bg-[#FFF5F5] rounded-lg p-4 border border-[#E5B5B0]">
                <p className="font-medium text-[#C24A3B] mb-1">Cross-Plan Protection</p>
                <p className="text-[#64645F]">Both MEC and Standard plans respect the global ceiling. Even preventive claims over the threshold are held for verification.</p>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* BRIDGE PAYMENT TAB */}
        <TabsContent value="bridge" className="mt-6 space-y-6">
          <div className="container-card">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Bridge Payment System</h2>
                <p className="text-xs text-[#8A8A85] mt-1">Allow members short on hours to pay the cash difference to maintain eligibility</p>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bridgeConfig.enabled}
                    onChange={(e) => setBridgeConfig({ ...bridgeConfig, enabled: e.target.checked })}
                    className="h-4 w-4 rounded"
                    data-testid="bridge-enabled"
                  />
                  <span className="text-sm font-medium text-[#1C1C1A]">Enabled</span>
                </label>
                <Badge className={bridgeConfig.enabled ? 'bg-[#5C2D91] text-white border-0' : 'bg-[#F0F0EA] text-[#8A8A85] border-0'}>
                  {bridgeConfig.enabled ? 'Active' : 'Disabled'}
                </Badge>
              </div>
            </div>

            <div className={`rounded-xl p-5 border-2 transition-all max-w-md ${bridgeConfig.enabled ? 'border-[#5C2D91] bg-[#F9F5FF]' : 'border-[#E2E2DF] bg-[#F7F7F4] opacity-60'}`} data-testid="bridge-config-card">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-[#5C2D91] flex items-center justify-center"><DollarSign className="h-4 w-4 text-white" /></div>
                <div>
                  <p className="font-medium text-sm text-[#1C1C1A] font-['Outfit']">Rate Per Hour</p>
                  <p className="text-[10px] text-[#8A8A85]">Cash cost per hour of coverage shortfall</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-xs">Cost per hour ($)</Label>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[#64645F]">$</span>
                  <Input
                    type="number"
                    step="0.50"
                    value={bridgeConfig.rate_per_hour}
                    onChange={(e) => setBridgeConfig({ ...bridgeConfig, rate_per_hour: parseFloat(e.target.value) || 0 })}
                    className="input-field max-w-[120px]"
                    disabled={!bridgeConfig.enabled}
                    data-testid="bridge-rate-input"
                  />
                  <span className="text-xs text-[#8A8A85]">/ hr</span>
                </div>
              </div>
              <div className="mt-4 text-xs text-[#64645F] bg-white rounded-md p-2.5 border border-[#E2E2DF]">
                Example: A member 10 hours short pays <span className="font-['JetBrains_Mono'] font-semibold">${(10 * bridgeConfig.rate_per_hour).toFixed(2)}</span> to restore active coverage and release held claims.
              </div>
            </div>

            <div className="flex items-center justify-between mt-6 pt-4 border-t border-[#E2E2DF]">
              <div className="flex items-center gap-2 text-xs text-[#8A8A85]">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Bridge payments are logged in the member audit trail and hour bank ledger.</span>
              </div>
              <Button onClick={saveBridge} disabled={bridgeSaving} className="bg-[#5C2D91] hover:bg-[#4a2475] text-white" data-testid="save-bridge-btn">
                {bridgeSaving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                Save Bridge Config
              </Button>
            </div>
          </div>

          {/* How Bridge Works */}
          <div className="container-card">
            <h3 className="text-sm font-medium text-[#1C1C1A] font-['Outfit'] mb-4">How Bridge Payments Work</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="bg-[#F9F5FF] rounded-lg p-4 border border-[#D8C8E8]">
                <p className="font-medium text-[#5C2D91] mb-1">1. Shortfall Detection</p>
                <p className="text-[#64645F]">When monthly calculation runs and a member falls below the eligibility threshold, the system calculates the exact hours shortfall.</p>
              </div>
              <div className="bg-[#F9F5FF] rounded-lg p-4 border border-[#D8C8E8]">
                <p className="font-medium text-[#5C2D91] mb-1">2. Cash Conversion</p>
                <p className="text-[#64645F]">Hours short × rate per hour = bridge payment amount. This is logged as a ledger entry with full audit trail.</p>
              </div>
              <div className="bg-[#F9F5FF] rounded-lg p-4 border border-[#D8C8E8]">
                <p className="font-medium text-[#5C2D91] mb-1">3. Instant Activation</p>
                <p className="text-[#64645F]">On payment, member status flips to Active, held claims are released for processing, and the eligibility source is stamped "Bridge Payment".</p>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* USERS TAB */}
        <TabsContent value="users" className="mt-6 space-y-6">
          <div className="container-card">
            <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Create User</h2>
            <form onSubmit={createUser} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Name</Label><Input value={userForm.name} onChange={(e) => setUserForm({ ...userForm, name: e.target.value })} className="input-field" required data-testid="user-name" /></div>
              <div className="space-y-2"><Label>Email</Label><Input type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} className="input-field" required data-testid="user-email" /></div>
              <div className="space-y-2"><Label>Password</Label><Input type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} className="input-field" required data-testid="user-password" /></div>
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={userForm.role} onValueChange={(v) => setUserForm({ ...userForm, role: v })}>
                  <SelectTrigger data-testid="user-role"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="adjudicator">Adjudicator</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-full flex justify-end">
                <Button type="submit" disabled={saving} className="btn-primary" data-testid="create-user-btn">
                  {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Create User'}
                </Button>
              </div>
            </form>
          </div>

          <div className="container-card p-0 overflow-hidden">
            <div className="p-4 border-b border-[#E2E2DF]"><h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">System Users</h2></div>
            {loading ? (
              <div className="flex items-center justify-center h-32"><RefreshCw className="h-6 w-6 text-[#1A3636] animate-spin" /></div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((u) => (
                    <TableRow key={u.id || u.email} className="table-row">
                      <TableCell className="font-medium">{u.name}</TableCell>
                      <TableCell className="text-xs text-[#64645F]">{u.email}</TableCell>
                      <TableCell><Badge className={u.role === 'admin' ? 'bg-[#1A3636] text-white border-0' : 'bg-[#F0F0EA] text-[#64645F] border-0'}>{u.role}</Badge></TableCell>
                      <TableCell className="text-xs text-[#8A8A85]">{u.created_at?.split('T')[0]}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* SYSTEM TAB */}
        <TabsContent value="system" className="mt-6">
          <div className="container-card">
            <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">System Configuration</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <p className="text-xs text-[#8A8A85]">Authentication</p>
                <p className="text-sm font-medium">Microsoft MSAL / JWT Fallback</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <p className="text-xs text-[#8A8A85]">Database</p>
                <p className="text-sm font-medium">MongoDB</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <p className="text-xs text-[#8A8A85]">Coverage Lines</p>
                <p className="text-sm font-medium">Medical, Dental, Vision, Hearing</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <p className="text-xs text-[#8A8A85]">Procedure Codes</p>
                <p className="text-sm font-medium">440 (189 Med + 79 Den + 44 Vis + 65 Hear + 63 Prev)</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <p className="text-xs text-[#8A8A85]">GPCI Localities</p>
                <p className="text-sm font-medium">87</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <p className="text-xs text-[#8A8A85]">EDI Standards</p>
                <p className="text-sm font-medium">834 / 837 / 835</p>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
