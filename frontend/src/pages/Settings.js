import { useState, useEffect } from 'react';
import api from '../lib/api';
import { settingsAPI, sftpAPI } from '../lib/api';
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
  Send,
  Trash2,
  Server,
  Play,
  Power,
  FileCheck,
  FileText,
  Calendar,
  CheckCircle,
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

  // Vendor state
  const [vendors, setVendors] = useState([]);
  const [vendorForm, setVendorForm] = useState({
    name: '', vendor_type: 'medical_tpa', feed_types: ['834'], format: 'hipaa_5010', sftp_host: '', sftp_path: '', enabled: true,
  });
  const [vendorSaving, setVendorSaving] = useState(false);

  // SFTP state
  const [sftpConnections, setSftpConnections] = useState([]);
  const [sftpSchedules, setSftpSchedules] = useState([]);
  const [sftpForm, setSftpForm] = useState({
    name: '', host: '', port: 22, username: '', auth_type: 'password', password: '', ssh_key: '', base_path: '/', enabled: true,
  });
  const [sftpSaving, setSftpSaving] = useState(false);
  const [testingConn, setTestingConn] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [scheduleForm, setScheduleForm] = useState({
    name: '', connection_id: '', frequency: 'daily', time_of_day: '02:00', day_of_week: 'mon', file_pattern: '*', route_type: '834', enabled: true,
  });
  const [scheduleSaving, setScheduleSaving] = useState(false);

  useEffect(() => {
    fetchUsers();
    fetchGatewayConfig();
    fetchBridgeConfig();
    fetchVendors();
    fetchSftpData();
  }, []);

  const fetchSftpData = async () => {
    try {
      const [conns, scheds] = await Promise.all([sftpAPI.getConnections(), sftpAPI.getSchedules()]);
      setSftpConnections(conns.data);
      setSftpSchedules(scheds.data);
    } catch { /* ok */ }
  };

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

  const fetchVendors = async () => {
    try {
      const res = await settingsAPI.getVendors();
      setVendors(res.data);
    } catch { /* ok */ }
  };

  const createVendor = async () => {
    if (!vendorForm.name) { toast.error('Vendor name is required'); return; }
    setVendorSaving(true);
    try {
      await settingsAPI.createVendor(vendorForm);
      toast.success(`Vendor "${vendorForm.name}" created`);
      setVendorForm({ name: '', vendor_type: 'medical_tpa', feed_types: ['834'], format: 'hipaa_5010', sftp_host: '', sftp_path: '', enabled: true });
      fetchVendors();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create vendor'); }
    finally { setVendorSaving(false); }
  };

  const deleteVendor = async (id) => {
    try {
      await settingsAPI.deleteVendor(id);
      toast.success('Vendor deleted');
      fetchVendors();
    } catch { toast.error('Failed to delete vendor'); }
  };

  const toggleVendorFormat = async (vendor) => {
    const newFormat = vendor.format === 'hipaa_5010' ? 'csv' : 'hipaa_5010';
    try {
      await settingsAPI.updateVendor(vendor.id, { ...vendor, format: newFormat });
      toast.success(`${vendor.name} switched to ${newFormat === 'hipaa_5010' ? 'HIPAA 5010' : 'CSV'}`);
      fetchVendors();
    } catch { toast.error('Failed to update vendor'); }
  };

  // ── SFTP Actions ──
  const createSftpConnection = async () => {
    if (!sftpForm.name || !sftpForm.host || !sftpForm.username) { toast.error('Name, Host, and Username are required'); return; }
    setSftpSaving(true);
    try {
      await sftpAPI.createConnection(sftpForm);
      toast.success(`Connection "${sftpForm.name}" created`);
      setSftpForm({ name: '', host: '', port: 22, username: '', auth_type: 'password', password: '', ssh_key: '', base_path: '/', enabled: true });
      fetchSftpData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create connection'); }
    finally { setSftpSaving(false); }
  };

  const deleteSftpConnection = async (id) => {
    try {
      await sftpAPI.deleteConnection(id);
      toast.success('Connection deleted');
      fetchSftpData();
    } catch { toast.error('Failed to delete connection'); }
  };

  const testSftpConnection = async (id) => {
    setTestingConn(id);
    setTestResult(null);
    try {
      const res = await sftpAPI.testConnection(id);
      setTestResult({ id, ...res.data });
      if (res.data.success) toast.success('Connection successful');
      else toast.error(`Connection failed: ${res.data.message}`);
    } catch (err) { setTestResult({ id, success: false, message: err.response?.data?.detail || 'Test failed' }); toast.error('Connection test failed'); }
    finally { setTestingConn(null); }
  };

  const testInlineConnection = async () => {
    if (!sftpForm.host || !sftpForm.username) { toast.error('Enter host and username first'); return; }
    setTestingConn('inline');
    setTestResult(null);
    try {
      const res = await sftpAPI.testInline(sftpForm);
      setTestResult({ id: 'inline', ...res.data });
      if (res.data.success) toast.success('Connection successful');
      else toast.error(`Test failed: ${res.data.message}`);
    } catch (err) { toast.error(err.response?.data?.detail || 'Test failed'); }
    finally { setTestingConn(null); }
  };

  const createSchedule = async () => {
    if (!scheduleForm.name || !scheduleForm.connection_id) { toast.error('Name and Connection are required'); return; }
    setScheduleSaving(true);
    try {
      await sftpAPI.createSchedule(scheduleForm);
      toast.success(`Schedule "${scheduleForm.name}" created`);
      setScheduleForm({ name: '', connection_id: '', frequency: 'daily', time_of_day: '02:00', day_of_week: 'mon', file_pattern: '*', route_type: '834', enabled: true });
      fetchSftpData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create schedule'); }
    finally { setScheduleSaving(false); }
  };

  const deleteSchedule = async (id) => {
    try {
      await sftpAPI.deleteSchedule(id);
      toast.success('Schedule deleted');
      fetchSftpData();
    } catch { toast.error('Failed to delete schedule'); }
  };

  const toggleSchedule = async (id) => {
    try {
      const res = await sftpAPI.toggleSchedule(id);
      toast.success(res.data.enabled ? 'Schedule enabled' : 'Schedule disabled');
      fetchSftpData();
    } catch { toast.error('Failed to toggle schedule'); }
  };

  const triggerScheduleNow = async (id) => {
    try {
      await sftpAPI.runNow(id);
      toast.success('Schedule triggered — check Intake History');
    } catch { toast.error('Failed to trigger schedule'); }
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
          <TabsTrigger value="vendors" className="data-[state=active]:bg-white text-sm" data-testid="tab-vendors"><Send className="h-3.5 w-3.5 mr-1.5" />Feed Vendors</TabsTrigger>
          <TabsTrigger value="sftp" className="data-[state=active]:bg-white text-sm" data-testid="tab-sftp"><Server className="h-3.5 w-3.5 mr-1.5" />SFTP Scheduler</TabsTrigger>
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

        {/* VENDORS TAB */}
        <TabsContent value="vendors" className="mt-6 space-y-6">
          <div className="container-card">
            <div className="mb-6">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Feed Vendor Configuration</h2>
              <p className="text-xs text-[#8A8A85] mt-1">Map outbound EDI feeds to specific vendors. Toggle between HIPAA 5010 and CSV per vendor.</p>
            </div>

            {/* Create Vendor Form */}
            <div className="bg-[#F7F7F4] rounded-xl p-4 mb-5 border border-[#E2E2DF]" data-testid="vendor-form">
              <p className="text-xs font-medium text-[#64645F] mb-3">Add New Vendor</p>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-[10px]">Vendor Name</Label>
                  <Input value={vendorForm.name} onChange={(e) => setVendorForm({...vendorForm, name: e.target.value})} placeholder="e.g. Acme PBM" className="input-field h-8 text-xs" data-testid="vendor-name-input" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Type</Label>
                  <Select value={vendorForm.vendor_type} onValueChange={(v) => setVendorForm({...vendorForm, vendor_type: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="vendor-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="medical_tpa">Medical TPA</SelectItem>
                      <SelectItem value="pbm">PBM</SelectItem>
                      <SelectItem value="dental_tpa">Dental TPA</SelectItem>
                      <SelectItem value="carrier">Carrier</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Feed Types</Label>
                  <Select value={vendorForm.feed_types.join(',')} onValueChange={(v) => setVendorForm({...vendorForm, feed_types: v.split(',')})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="vendor-feeds-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="834">834 Only</SelectItem>
                      <SelectItem value="278">278 Only</SelectItem>
                      <SelectItem value="834,278">834 + 278</SelectItem>
                      <SelectItem value="834,278,835">All (834/278/835)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Default Format</Label>
                  <Select value={vendorForm.format} onValueChange={(v) => setVendorForm({...vendorForm, format: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="vendor-format-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hipaa_5010">HIPAA 5010</SelectItem>
                      <SelectItem value="csv">Custom CSV</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={createVendor} disabled={vendorSaving} size="sm" className="btn-primary h-8 text-xs" data-testid="create-vendor-btn">
                  {vendorSaving ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Zap className="h-3 w-3 mr-1" />}Add Vendor
                </Button>
              </div>
            </div>

            {/* Vendor List */}
            {vendors.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">No vendors configured. Add one above.</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]">
                  <TableHead>Vendor Name</TableHead><TableHead>Type</TableHead><TableHead>Feed Types</TableHead><TableHead>Format</TableHead><TableHead>Status</TableHead><TableHead className="w-[80px]"></TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {vendors.map((v) => (
                    <TableRow key={v.id} className="table-row h-[48px]" data-testid={`vendor-row-${v.id}`}>
                      <TableCell className="text-sm font-medium">{v.name}</TableCell>
                      <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px] capitalize">{v.vendor_type?.replace(/_/g, ' ')}</Badge></TableCell>
                      <TableCell className="text-xs">{v.feed_types?.join(', ')}</TableCell>
                      <TableCell>
                        <Button variant="outline" size="sm" onClick={() => toggleVendorFormat(v)} className="h-7 text-[10px] px-2" data-testid={`toggle-format-${v.id}`}>
                          {v.format === 'hipaa_5010' ? (
                            <><Shield className="h-3 w-3 mr-1 text-[#1A3636]" />HIPAA 5010</>
                          ) : (
                            <><FileText className="h-3 w-3 mr-1 text-[#C9862B]" />CSV</>
                          )}
                        </Button>
                      </TableCell>
                      <TableCell><Badge className={v.enabled ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : 'bg-[#8A8A85] text-white border-0 text-[9px]'}>{v.enabled ? 'Active' : 'Disabled'}</Badge></TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => deleteVendor(v.id)} className="h-7 w-7 p-0 text-[#C24A3B]" data-testid={`delete-vendor-${v.id}`}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* SFTP SCHEDULER TAB */}
        <TabsContent value="sftp" className="mt-6 space-y-6">
          {/* Connection Manager */}
          <div className="container-card">
            <div className="mb-6">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">SFTP Connection Manager</h2>
              <p className="text-xs text-[#8A8A85] mt-1">Configure remote SFTP servers for automated file intake. Credentials are encrypted at rest.</p>
            </div>

            <div className="bg-[#F7F7F4] rounded-xl p-4 mb-5 border border-[#E2E2DF]" data-testid="sftp-connection-form">
              <p className="text-xs font-medium text-[#64645F] mb-3">New Connection</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-[10px]">Connection Name</Label>
                  <Input value={sftpForm.name} onChange={(e) => setSftpForm({...sftpForm, name: e.target.value})} placeholder="e.g. Acme SFTP" className="input-field h-8 text-xs" data-testid="sftp-name-input" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Host</Label>
                  <Input value={sftpForm.host} onChange={(e) => setSftpForm({...sftpForm, host: e.target.value})} placeholder="sftp.acme.com" className="input-field h-8 text-xs" data-testid="sftp-host-input" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Port</Label>
                  <Input type="number" value={sftpForm.port} onChange={(e) => setSftpForm({...sftpForm, port: parseInt(e.target.value) || 22})} className="input-field h-8 text-xs" data-testid="sftp-port-input" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Username</Label>
                  <Input value={sftpForm.username} onChange={(e) => setSftpForm({...sftpForm, username: e.target.value})} placeholder="sftp_user" className="input-field h-8 text-xs" data-testid="sftp-username-input" />
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end mt-3">
                <div className="space-y-1">
                  <Label className="text-[10px]">Auth Type</Label>
                  <Select value={sftpForm.auth_type} onValueChange={(v) => setSftpForm({...sftpForm, auth_type: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="sftp-auth-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="password">Password</SelectItem>
                      <SelectItem value="key">SSH Key</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {sftpForm.auth_type === 'password' ? (
                  <div className="space-y-1">
                    <Label className="text-[10px]">Password</Label>
                    <Input type="password" value={sftpForm.password} onChange={(e) => setSftpForm({...sftpForm, password: e.target.value})} className="input-field h-8 text-xs" data-testid="sftp-password-input" />
                  </div>
                ) : (
                  <div className="space-y-1 col-span-2">
                    <Label className="text-[10px]">SSH Private Key (PEM)</Label>
                    <Input value={sftpForm.ssh_key} onChange={(e) => setSftpForm({...sftpForm, ssh_key: e.target.value})} placeholder="Paste PEM key" className="input-field h-8 text-xs" data-testid="sftp-key-input" />
                  </div>
                )}
                <div className="space-y-1">
                  <Label className="text-[10px]">Base Path</Label>
                  <Input value={sftpForm.base_path} onChange={(e) => setSftpForm({...sftpForm, base_path: e.target.value})} placeholder="/outbound" className="input-field h-8 text-xs" data-testid="sftp-basepath-input" />
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={testInlineConnection} disabled={testingConn === 'inline'} className="h-8 text-xs flex-1" data-testid="sftp-test-inline-btn">
                    {testingConn === 'inline' ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Zap className="h-3 w-3 mr-1" />}Test
                  </Button>
                  <Button onClick={createSftpConnection} disabled={sftpSaving} size="sm" className="btn-primary h-8 text-xs flex-1" data-testid="sftp-create-btn">
                    {sftpSaving ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Save className="h-3 w-3 mr-1" />}Save
                  </Button>
                </div>
              </div>
              {testResult?.id === 'inline' && (
                <div className={`mt-3 p-2.5 rounded-lg text-xs ${testResult.success ? 'bg-[#F0F7F1] text-[#4B6E4E] border border-[#4B6E4E]/20' : 'bg-[#FFF5F5] text-[#C24A3B] border border-[#C24A3B]/20'}`} data-testid="sftp-inline-test-result">
                  {testResult.success ? <CheckCircle className="h-3 w-3 inline mr-1" /> : <AlertTriangle className="h-3 w-3 inline mr-1" />}{testResult.message}
                </div>
              )}
            </div>

            {sftpConnections.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">No SFTP connections. Add one above.</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]">
                  <TableHead>Name</TableHead><TableHead>Host</TableHead><TableHead>Port</TableHead><TableHead>User</TableHead><TableHead>Auth</TableHead><TableHead>Path</TableHead><TableHead>Status</TableHead><TableHead className="w-[120px]"></TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {sftpConnections.map((c) => (
                    <TableRow key={c.id} className="table-row h-[48px]" data-testid={`sftp-conn-row-${c.id}`}>
                      <TableCell className="text-sm font-medium">{c.name}</TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono']">{c.host}</TableCell>
                      <TableCell className="text-xs tabular-nums">{c.port}</TableCell>
                      <TableCell className="text-xs">{c.username}</TableCell>
                      <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]">{c.auth_type}</Badge></TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono']">{c.base_path}</TableCell>
                      <TableCell><Badge className={c.enabled ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : 'bg-[#8A8A85] text-white border-0 text-[9px]'}>{c.enabled ? 'Active' : 'Disabled'}</Badge></TableCell>
                      <TableCell className="flex gap-1">
                        <Button variant="outline" size="sm" onClick={() => testSftpConnection(c.id)} disabled={testingConn === c.id} className="h-7 text-[10px] px-2" data-testid={`test-sftp-${c.id}`}>
                          {testingConn === c.id ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Zap className="h-3 w-3" />}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => deleteSftpConnection(c.id)} className="h-7 w-7 p-0 text-[#C24A3B]" data-testid={`delete-sftp-${c.id}`}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            {/* Test result banner for saved connections */}
            {testResult && testResult.id !== 'inline' && (
              <div className={`mt-3 p-2.5 rounded-lg text-xs ${testResult.success ? 'bg-[#F0F7F1] text-[#4B6E4E] border border-[#4B6E4E]/20' : 'bg-[#FFF5F5] text-[#C24A3B] border border-[#C24A3B]/20'}`} data-testid="sftp-saved-test-result">
                {testResult.success ? <CheckCircle className="h-3 w-3 inline mr-1" /> : <AlertTriangle className="h-3 w-3 inline mr-1" />}{testResult.message}
              </div>
            )}
          </div>

          {/* Intake Scheduling */}
          <div className="container-card">
            <div className="mb-6">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Automated Intake Scheduling</h2>
              <p className="text-xs text-[#8A8A85] mt-1">Define when files are fetched and how they're routed. File masks filter by name pattern.</p>
            </div>

            <div className="bg-[#F7F7F4] rounded-xl p-4 mb-5 border border-[#E2E2DF]" data-testid="sftp-schedule-form">
              <p className="text-xs font-medium text-[#64645F] mb-3">New Schedule</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-[10px]">Schedule Name</Label>
                  <Input value={scheduleForm.name} onChange={(e) => setScheduleForm({...scheduleForm, name: e.target.value})} placeholder="e.g. Daily 834 Sync" className="input-field h-8 text-xs" data-testid="sched-name-input" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">SFTP Connection</Label>
                  <Select value={scheduleForm.connection_id} onValueChange={(v) => setScheduleForm({...scheduleForm, connection_id: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="sched-connection-select"><SelectValue placeholder="Select..." /></SelectTrigger>
                    <SelectContent>
                      {sftpConnections.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Frequency</Label>
                  <Select value={scheduleForm.frequency} onValueChange={(v) => setScheduleForm({...scheduleForm, frequency: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="sched-freq-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hourly">Hourly</SelectItem>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {scheduleForm.frequency !== 'hourly' && (
                  <div className="space-y-1">
                    <Label className="text-[10px]">Time (UTC)</Label>
                    <Input type="time" value={scheduleForm.time_of_day} onChange={(e) => setScheduleForm({...scheduleForm, time_of_day: e.target.value})} className="input-field h-8 text-xs" data-testid="sched-time-input" />
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end mt-3">
                {scheduleForm.frequency === 'weekly' && (
                  <div className="space-y-1">
                    <Label className="text-[10px]">Day of Week</Label>
                    <Select value={scheduleForm.day_of_week} onValueChange={(v) => setScheduleForm({...scheduleForm, day_of_week: v})}>
                      <SelectTrigger className="input-field h-8 text-xs" data-testid="sched-dow-select"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {['mon','tue','wed','thu','fri','sat','sun'].map(d => <SelectItem key={d} value={d}>{d.charAt(0).toUpperCase()+d.slice(1)}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="space-y-1">
                  <Label className="text-[10px]">File Name Pattern</Label>
                  <Input value={scheduleForm.file_pattern} onChange={(e) => setScheduleForm({...scheduleForm, file_pattern: e.target.value})} placeholder="*834_Acme_*.dat" className="input-field h-8 text-xs font-['JetBrains_Mono']" data-testid="sched-pattern-input" />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Route To</Label>
                  <Select value={scheduleForm.route_type} onValueChange={(v) => setScheduleForm({...scheduleForm, route_type: v})}>
                    <SelectTrigger className="input-field h-8 text-xs" data-testid="sched-route-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="834">834 &rarr; Member Enrollment</SelectItem>
                      <SelectItem value="835">835/Claims &rarr; Adjudication</SelectItem>
                      <SelectItem value="work_report">Work Report &rarr; Hour Bank</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={createSchedule} disabled={scheduleSaving} size="sm" className="btn-primary h-8 text-xs" data-testid="sched-create-btn">
                  {scheduleSaving ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Calendar className="h-3 w-3 mr-1" />}Create Schedule
                </Button>
              </div>
            </div>

            {sftpSchedules.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-6 text-center"><p className="text-sm text-[#8A8A85]">No schedules configured. Create one above.</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]">
                  <TableHead>Name</TableHead><TableHead>Connection</TableHead><TableHead>Frequency</TableHead><TableHead>Pattern</TableHead><TableHead>Route</TableHead><TableHead>Status</TableHead><TableHead>Last Run</TableHead><TableHead className="w-[120px]"></TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {sftpSchedules.map((s) => (
                    <TableRow key={s.id} className="table-row h-[48px]" data-testid={`sched-row-${s.id}`}>
                      <TableCell className="text-sm font-medium">{s.name}</TableCell>
                      <TableCell className="text-xs">{s.connection_name}</TableCell>
                      <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px] capitalize">{s.frequency}{s.frequency === 'daily' ? ` @ ${s.time_of_day}` : s.frequency === 'weekly' ? ` ${s.day_of_week} @ ${s.time_of_day}` : ''}</Badge></TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono']">{s.file_pattern}</TableCell>
                      <TableCell><Badge className={
                        s.route_type === '834' ? 'bg-[#1A3636] text-white border-0 text-[10px]' :
                        s.route_type === 'work_report' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                        'bg-[#4A6FA5] text-white border-0 text-[10px]'
                      }>{s.route_type === '834' ? 'Enrollment' : s.route_type === 'work_report' ? 'Hour Bank' : 'Adjudication'}</Badge></TableCell>
                      <TableCell><Badge className={s.enabled ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : 'bg-[#8A8A85] text-white border-0 text-[9px]'}>{s.enabled ? 'Active' : 'Paused'}</Badge></TableCell>
                      <TableCell className="text-[10px] text-[#8A8A85] tabular-nums">{s.last_run ? new Date(s.last_run).toLocaleString() : 'Never'}</TableCell>
                      <TableCell className="flex gap-1">
                        <Button variant="outline" size="sm" onClick={() => triggerScheduleNow(s.id)} className="h-7 text-[10px] px-2" title="Run Now" data-testid={`run-sched-${s.id}`}>
                          <Play className="h-3 w-3" />
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => toggleSchedule(s.id)} className="h-7 text-[10px] px-2" title="Toggle" data-testid={`toggle-sched-${s.id}`}>
                          <Power className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => deleteSchedule(s.id)} className="h-7 w-7 p-0 text-[#C24A3B]" data-testid={`delete-sched-${s.id}`}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          {/* Routing Logic Reference */}
          <div className="container-card">
            <h3 className="text-sm font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Intelligent Routing Logic</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="bg-[#F0F7F1] rounded-lg p-4 border border-[#D4E5D6]">
                <div className="flex items-center gap-2 mb-2"><Shield className="h-4 w-4 text-[#1A3636]" /><p className="font-medium text-[#1A3636]">834 Files &rarr; Enrollment</p></div>
                <p className="text-[#64645F]">X12 or pipe-delimited 834 files are parsed and routed to the Member Enrollment engine. Adds, terms, and reinstatements are processed automatically.</p>
              </div>
              <div className="bg-[#EFF4FB] rounded-lg p-4 border border-[#C8D8EE]">
                <div className="flex items-center gap-2 mb-2"><FileCheck className="h-4 w-4 text-[#4A6FA5]" /><p className="font-medium text-[#4A6FA5]">835/Claims &rarr; Adjudication</p></div>
                <p className="text-[#64645F]">837 claims files are parsed and submitted to the adjudication gateway. Tiered authorization rules apply automatically (Tier 1/2/3).</p>
              </div>
              <div className="bg-[#F9F5FF] rounded-lg p-4 border border-[#D8C8E8]">
                <div className="flex items-center gap-2 mb-2"><DollarSign className="h-4 w-4 text-[#5C2D91]" /><p className="font-medium text-[#5C2D91]">Work Reports &rarr; Hour Bank</p></div>
                <p className="text-[#64645F]">CSV work reports (MemberID, Hours, Period) credit member hour banks. Unknown members are flagged in the Duplicates & Errors queue.</p>
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
