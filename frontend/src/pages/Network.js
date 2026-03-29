import { useState, useEffect } from 'react';
import { networkAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Globe,
  Plus,
  RefreshCw,
  DollarSign,
  TrendingDown,
  Building2,
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';

export default function Network() {
  const [contracts, setContracts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    provider_npi: '',
    provider_name: '',
    network_name: '',
    contract_type: 'percent_medicare',
    multiplier: 1.2,
    effective_date: new Date().toISOString().split('T')[0],
    termination_date: '',
    coverage_types: ['medical'],
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [contractsRes, summaryRes] = await Promise.all([
        networkAPI.contracts(),
        networkAPI.summary(),
      ]);
      setContracts(contractsRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      toast.error('Failed to load network data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await networkAPI.createContract(form);
      toast.success('Network contract created');
      setShowCreate(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create contract');
    } finally {
      setSaving(false);
    }
  };

  const formatCurrency = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value || 0);

  return (
    <div className="space-y-6" data-testid="network-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Network Management</h1>
          <p className="text-sm text-[#64645F] mt-1">Provider contracts and network repricing</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="new-contract-btn">
            <Plus className="h-4 w-4 mr-2" />New Contract
          </Button>
          <Button onClick={fetchData} variant="outline" className="btn-secondary" data-testid="refresh-network-btn">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="metric-card">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="h-4 w-4 text-[#64645F]" />
              <span className="metric-label">Active Contracts</span>
            </div>
            <p className="metric-value">{summary.active_contracts}</p>
          </div>
          <div className="metric-card">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-[#64645F]" />
              <span className="metric-label">Total Billed</span>
            </div>
            <p className="metric-value">{formatCurrency(summary.total_billed)}</p>
          </div>
          <div className="metric-card">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-[#4B6E4E]" />
              <span className="metric-label">Total Paid</span>
            </div>
            <p className="metric-value text-[#4B6E4E]">{formatCurrency(summary.total_paid)}</p>
          </div>
          <div className="metric-card">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="h-4 w-4 text-[#C24A3B]" />
              <span className="metric-label">Total Savings</span>
            </div>
            <p className="metric-value text-[#C24A3B]">{formatCurrency(summary.total_savings)}</p>
            <p className="text-xs text-[#64645F] mt-1">{summary.savings_percentage}% of billed</p>
          </div>
        </div>
      )}

      <div className="container-card p-0 overflow-hidden">
        <div className="p-6 border-b border-[#E2E2DF]">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Provider Contracts</h3>
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
        ) : contracts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Globe className="h-12 w-12 text-[#E2E2DF] mb-4" />
            <p className="text-[#64645F]">No network contracts</p>
            <p className="text-sm text-[#8A8A85]">Create provider contracts for network repricing</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>Provider</TableHead>
                <TableHead>NPI</TableHead>
                <TableHead>Network</TableHead>
                <TableHead>Contract Type</TableHead>
                <TableHead>Multiplier</TableHead>
                <TableHead>Coverage</TableHead>
                <TableHead>Effective</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contracts.map((c) => (
                <TableRow key={c.id} className="table-row hover:bg-[#F7F7F4] transition-colors" data-testid={`contract-row-${c.id}`}>
                  <TableCell className="font-medium max-w-[200px] truncate">{c.provider_name}</TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs">{c.provider_npi}</TableCell>
                  <TableCell>{c.network_name}</TableCell>
                  <TableCell className="capitalize">{c.contract_type?.replace('_', ' ')}</TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs">{(c.multiplier * 100).toFixed(0)}%</TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {c.coverage_types?.map((ct) => (
                        <Badge key={ct} variant="outline" className="text-xs capitalize">{ct}</Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{c.effective_date}</TableCell>
                  <TableCell><Badge className="badge-approved">{c.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Create Contract Modal */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">New Network Contract</DialogTitle>
            <DialogDescription>Add a provider to a network with contracted rates</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid grid-cols-2 gap-4 py-4">
              <div className="space-y-2">
                <Label>Provider NPI</Label>
                <Input value={form.provider_npi} onChange={(e) => setForm({ ...form, provider_npi: e.target.value })} className="input-field" required data-testid="contract-npi" />
              </div>
              <div className="space-y-2">
                <Label>Provider Name</Label>
                <Input value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} className="input-field" required data-testid="contract-name" />
              </div>
              <div className="space-y-2">
                <Label>Network Name</Label>
                <Input value={form.network_name} onChange={(e) => setForm({ ...form, network_name: e.target.value })} className="input-field" placeholder="e.g., Blue Network" required data-testid="contract-network" />
              </div>
              <div className="space-y-2">
                <Label>Contract Type</Label>
                <Select value={form.contract_type} onValueChange={(v) => setForm({ ...form, contract_type: v })}>
                  <SelectTrigger data-testid="contract-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percent_medicare">% of Medicare</SelectItem>
                    <SelectItem value="fee_schedule">Fee Schedule</SelectItem>
                    <SelectItem value="percent_billed">% of Billed</SelectItem>
                    <SelectItem value="case_rate">Case Rate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Rate Multiplier</Label>
                <Input type="number" step="0.01" value={form.multiplier} onChange={(e) => setForm({ ...form, multiplier: parseFloat(e.target.value) })} className="input-field" min="0" data-testid="contract-multiplier" />
              </div>
              <div className="space-y-2">
                <Label>Effective Date</Label>
                <Input type="date" value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} className="input-field" required data-testid="contract-effective" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</Button>
              <Button type="submit" disabled={saving} className="btn-primary" data-testid="contract-submit">
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Create Contract'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
