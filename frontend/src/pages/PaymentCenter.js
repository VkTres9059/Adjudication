import { useState, useEffect } from 'react';
import { paymentsAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  DollarSign, RefreshCw, ArrowLeftRight, Ban, CreditCard, Building2,
  FileText, Plus, Filter, CheckCircle2, AlertTriangle, RotateCcw,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(v || 0);
const methodIcons = { ach: Building2, virtual_card: CreditCard, check: FileText };
const methodLabels = { ach: 'ACH', virtual_card: 'Virtual Card', check: 'Check' };
const statusColors = {
  pending: 'bg-[#C9862B] text-white', processed: 'bg-[#4A6FA5] text-white', cleared: 'bg-[#4B6E4E] text-white',
  reversed: 'bg-[#C24A3B] text-white', voided: 'bg-[#8A8A85] text-white',
};

export default function PaymentCenter() {
  const [tab, setTab] = useState('overview');
  const [summary, setSummary] = useState(null);
  const [payments, setPayments] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [batchMethod, setBatchMethod] = useState('ach');
  const [batchFunding, setBatchFunding] = useState('aso');
  const [reversalId, setReversalId] = useState('');
  const [reversalReason, setReversalReason] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sumRes, payRes, batchRes] = await Promise.all([
        paymentsAPI.summary(),
        paymentsAPI.list({ limit: 100 }),
        paymentsAPI.batches(),
      ]);
      setSummary(sumRes.data);
      setPayments(payRes.data);
      setBatches(batchRes.data);
    } catch { toast.error('Failed to load payments'); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const createBatch = async () => {
    try {
      const res = await paymentsAPI.createBatch({ payment_method: batchMethod, funding_source: batchFunding, description: 'UI batch run' });
      toast.success(`Batch created: ${res.data.payment_count} payments`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Batch creation failed');
    }
  };

  const handleReversal = async () => {
    if (!reversalId || !reversalReason) return toast.error('Payment ID and reason required');
    try {
      await paymentsAPI.reverse({ payment_id: reversalId, reason: reversalReason });
      toast.success('Payment reversed');
      setReversalId(''); setReversalReason('');
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Reversal failed'); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>;

  return (
    <div className="space-y-6" data-testid="payment-center-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">Payment Center</h1>
          <p className="text-sm text-[#64645F]">ACH, Virtual Card, Check — with full reconciliation and reversals</p>
        </div>
        <Button variant="outline" onClick={fetchData} className="text-xs"><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="payment-summary">
          <div className="container-card"><p className="text-[10px] text-[#8A8A85]">Total Payments</p><p className="text-2xl font-semibold font-['Outfit']">{summary.total_payments}</p></div>
          <div className="container-card"><p className="text-[10px] text-[#8A8A85]">Total Disbursed</p><p className="text-2xl font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(summary.total_amount)}</p></div>
          {Object.entries(summary.by_method || {}).map(([m, d]) => (
            <div key={m} className="container-card">
              <p className="text-[10px] text-[#8A8A85]">{methodLabels[m] || m}</p>
              <p className="text-xl font-semibold font-['JetBrains_Mono']">{fmt(d.total)}</p>
              <p className="text-[10px] text-[#64645F]">{d.count} payments</p>
            </div>
          ))}
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-[#F0F0EA] p-1 rounded-xl">
          <TabsTrigger value="overview" className="data-[state=active]:bg-white text-sm" data-testid="tab-payments-overview">
            <DollarSign className="h-3.5 w-3.5 mr-1" />Payments
          </TabsTrigger>
          <TabsTrigger value="batches" className="data-[state=active]:bg-white text-sm" data-testid="tab-batches">
            <Plus className="h-3.5 w-3.5 mr-1" />Batch Run
          </TabsTrigger>
          <TabsTrigger value="reversals" className="data-[state=active]:bg-white text-sm" data-testid="tab-reversals">
            <RotateCcw className="h-3.5 w-3.5 mr-1" />Reversals
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="container-card p-0 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="table-header">
                  <TableHead>Claim #</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="text-center py-8 text-sm text-[#8A8A85]">No payments yet — run a batch to create payments</TableCell></TableRow>
                ) : payments.map(p => (
                  <TableRow key={p.id} className="table-row" data-testid={`payment-${p.id}`}>
                    <TableCell className="font-['JetBrains_Mono'] text-xs">{p.claim_number}</TableCell>
                    <TableCell className="text-xs">{p.provider_name}</TableCell>
                    <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]">{methodLabels[p.payment_method] || p.payment_method}</Badge></TableCell>
                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold">{fmt(p.amount)}</TableCell>
                    <TableCell><Badge className={`border-0 text-[10px] ${statusColors[p.status] || 'bg-[#F0F0EA] text-[#64645F]'}`}>{p.status}</Badge></TableCell>
                    <TableCell className="text-[10px] text-[#8A8A85]">{p.created_at ? new Date(p.created_at).toLocaleDateString() : ''}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="batches" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-4 container-card" data-testid="batch-create-form">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Create Batch Run</h3>
              <div className="space-y-3">
                <div className="space-y-1">
                  <Label className="text-xs">Payment Method</Label>
                  <Select value={batchMethod} onValueChange={setBatchMethod}>
                    <SelectTrigger className="input-field"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ach">ACH</SelectItem>
                      <SelectItem value="virtual_card">Virtual Card</SelectItem>
                      <SelectItem value="check">Check</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Funding Source</Label>
                  <Select value={batchFunding} onValueChange={setBatchFunding}>
                    <SelectTrigger className="input-field"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="aso">ASO</SelectItem>
                      <SelectItem value="level_funded">Level Funded</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={createBatch} className="btn-primary w-full" data-testid="create-batch-btn">
                  <Plus className="h-4 w-4 mr-1" />Run Batch
                </Button>
              </div>
            </div>
            <div className="col-span-8 container-card" data-testid="batch-history">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-3">Batch History</h3>
              {batches.length === 0 ? (
                <p className="text-sm text-[#8A8A85] text-center py-6">No batches yet</p>
              ) : (
                <div className="space-y-2">
                  {batches.map(b => (
                    <div key={b.id} className="flex items-center justify-between p-3 bg-[#F7F7F4] rounded-lg border border-[#E2E2DF]">
                      <div>
                        <p className="text-sm font-medium">{b.payment_count} payments via {methodLabels[b.payment_method] || b.payment_method}</p>
                        <p className="text-[10px] text-[#8A8A85]">{b.funding_source} | {new Date(b.created_at).toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-['JetBrains_Mono'] text-sm font-semibold text-[#4B6E4E]">{fmt(b.total_amount)}</p>
                        <Badge className={`border-0 text-[9px] ${statusColors[b.status] || 'bg-[#F0F0EA] text-[#64645F]'}`}>{b.status}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="reversals" className="mt-4">
          <div className="container-card" data-testid="reversal-form">
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Reverse a Payment</h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="space-y-1">
                <Label className="text-xs">Payment ID</Label>
                <Input value={reversalId} onChange={e => setReversalId(e.target.value)} placeholder="Payment UUID" className="input-field" data-testid="reversal-payment-id" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Reason</Label>
                <Input value={reversalReason} onChange={e => setReversalReason(e.target.value)} placeholder="Reason for reversal" className="input-field" data-testid="reversal-reason" />
              </div>
              <div className="flex items-end">
                <Button onClick={handleReversal} className="bg-[#C24A3B] text-white hover:bg-[#A03D30]" data-testid="reverse-btn">
                  <RotateCcw className="h-4 w-4 mr-1" />Reverse Payment
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
