import { useState, useEffect } from 'react';
import { paymentsAPI, zelisAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  DollarSign, RefreshCw, ArrowLeftRight, Ban, CreditCard, Building2,
  FileText, Plus, Filter, CheckCircle2, AlertTriangle, RotateCcw,
  Zap, Globe, Send, ArrowRight,
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
const methodLabels = { ach: 'ACH', virtual_card: 'Virtual Card', check: 'Check', ach_plus: 'ACH+', zapp: 'ZAPP Digital' };
const statusColors = {
  pending: 'bg-[#C9862B] text-white', processed: 'bg-[#4A6FA5] text-white', cleared: 'bg-[#4B6E4E] text-white',
  reversed: 'bg-[#C24A3B] text-white', voided: 'bg-[#8A8A85] text-white',
  accepted: 'bg-[#4A6FA5] text-white', card_issued: 'bg-[#5C2D91] text-white', in_transit: 'bg-[#C9862B] text-white',
  processing: 'bg-[#C9862B] text-white', submitting: 'bg-[#8A8A85] text-white',
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

  // Zelis state
  const [zelisSummary, setZelisSummary] = useState(null);
  const [zelisTransactions, setZelisTransactions] = useState([]);
  const [zelisMethods, setZelisMethods] = useState([]);
  const [eraDocuments, setEraDocuments] = useState([]);
  const [zelisClaimId, setZelisClaimId] = useState('');
  const [zelisMethod, setZelisMethod] = useState('ach');
  const [zelisSubmitting, setZelisSubmitting] = useState(false);

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

  const fetchZelisData = async () => {
    try {
      const [sumRes, txRes, methodRes, eraRes] = await Promise.all([
        zelisAPI.summary(),
        zelisAPI.transactions({}),
        zelisAPI.methods(),
        zelisAPI.eraDocuments(),
      ]);
      setZelisSummary(sumRes.data);
      setZelisTransactions(txRes.data);
      setZelisMethods(methodRes.data.methods || []);
      setEraDocuments(eraRes.data);
    } catch {}
  };

  useEffect(() => { fetchData(); fetchZelisData(); }, []);

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

  const submitToZelis = async () => {
    if (!zelisClaimId.trim()) return toast.error('Claim ID required');
    setZelisSubmitting(true);
    try {
      const res = await zelisAPI.submit({ claim_id: zelisClaimId.trim(), payment_method: zelisMethod });
      toast.success(`Payment submitted via Zelis: ${res.data.zelis?.zelis_transaction_id}`);
      setZelisClaimId('');
      fetchZelisData();
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Zelis submission failed'); }
    finally { setZelisSubmitting(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>;

  return (
    <div className="space-y-6" data-testid="payment-center-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">Payment Center</h1>
          <p className="text-sm text-[#64645F]">ACH, Virtual Card, Check, Zelis Network — with full reconciliation and ERA 835</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-[#5C2D91] text-white border-0 text-[10px]">Zelis Payments</Badge>
          <Button variant="outline" onClick={() => { fetchData(); fetchZelisData(); }} className="text-xs"><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
        </div>
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
          <TabsTrigger value="zelis" className="data-[state=active]:bg-white text-sm" data-testid="tab-zelis">
            <Globe className="h-3.5 w-3.5 mr-1" />Zelis Network
          </TabsTrigger>
          <TabsTrigger value="era" className="data-[state=active]:bg-white text-sm" data-testid="tab-era">
            <FileText className="h-3.5 w-3.5 mr-1" />ERA 835
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

        {/* ── ZELIS NETWORK TAB ── */}
        <TabsContent value="zelis" className="mt-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-4 container-card" data-testid="zelis-submit-form">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-[#5C2D91] rounded-lg flex items-center justify-center">
                  <Zap className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-[#1C1C1A]">Submit via Zelis</h3>
                  <p className="text-[10px] text-[#8A8A85]">Healthcare payment network</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <Label className="text-xs">Claim ID</Label>
                  <Input value={zelisClaimId} onChange={e => setZelisClaimId(e.target.value)} placeholder="Claim UUID" className="input-field" data-testid="zelis-claim-id" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Payment Method</Label>
                  <Select value={zelisMethod} onValueChange={setZelisMethod}>
                    <SelectTrigger className="input-field"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {zelisMethods.map(m => (
                        <SelectItem key={m.id} value={m.id}>{m.label} {m.fee_pct > 0 ? `(${m.fee_pct}% fee)` : ''}</SelectItem>
                      ))}
                      {zelisMethods.length === 0 && <>
                        <SelectItem value="ach">ACH Direct Deposit</SelectItem>
                        <SelectItem value="virtual_card">Virtual Card (2.5%)</SelectItem>
                        <SelectItem value="check">Paper Check</SelectItem>
                        <SelectItem value="ach_plus">Zelis ACH+</SelectItem>
                        <SelectItem value="zapp">ZAPP Digital Card (1.8%)</SelectItem>
                      </>}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={submitToZelis} disabled={zelisSubmitting} className="btn-primary w-full" data-testid="zelis-submit-btn">
                  {zelisSubmitting ? <RefreshCw className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
                  Submit to Zelis
                </Button>
              </div>

              {/* Zelis Summary */}
              {zelisSummary && zelisSummary.total_transactions > 0 && (
                <div className="mt-4 pt-4 border-t border-[#E2E2DF]">
                  <p className="text-[10px] text-[#8A8A85] mb-2">Network Summary</p>
                  <div className="space-y-2">
                    <div className="flex justify-between"><span className="text-xs text-[#64645F]">Transactions</span><span className="text-xs font-['JetBrains_Mono']">{zelisSummary.total_transactions}</span></div>
                    <div className="flex justify-between"><span className="text-xs text-[#64645F]">Total Volume</span><span className="text-xs font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(zelisSummary.total_amount)}</span></div>
                    <div className="flex justify-between"><span className="text-xs text-[#64645F]">Processing Fees</span><span className="text-xs font-['JetBrains_Mono'] text-[#C24A3B]">{fmt(zelisSummary.total_processing_fees)}</span></div>
                  </div>
                </div>
              )}
            </div>

            <div className="col-span-8 container-card p-0 overflow-hidden" data-testid="zelis-transactions">
              <div className="p-4 border-b border-[#E2E2DF] flex items-center justify-between">
                <h3 className="text-sm font-medium text-[#1C1C1A]">Zelis Transactions</h3>
                <Button variant="outline" size="sm" onClick={fetchZelisData} className="text-[10px] h-6 px-2">
                  <RefreshCw className="h-3 w-3" />
                </Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead className="text-[10px]">Zelis ID</TableHead>
                    <TableHead className="text-[10px]">Claim #</TableHead>
                    <TableHead className="text-[10px]">Provider</TableHead>
                    <TableHead className="text-[10px]">Method</TableHead>
                    <TableHead className="text-right text-[10px]">Amount</TableHead>
                    <TableHead className="text-right text-[10px]">Fee</TableHead>
                    <TableHead className="text-[10px]">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {zelisTransactions.length === 0 ? (
                    <TableRow><TableCell colSpan={7} className="text-center py-8 text-sm text-[#8A8A85]">No Zelis transactions yet</TableCell></TableRow>
                  ) : zelisTransactions.map(tx => (
                    <TableRow key={tx.id} className="table-row" data-testid={`zelis-tx-${tx.id}`}>
                      <TableCell className="font-['JetBrains_Mono'] text-[10px]">{tx.zelis_transaction_id?.slice(0, 12)}</TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-[10px]">{tx.claim_number}</TableCell>
                      <TableCell className="text-xs">{tx.provider_name}</TableCell>
                      <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]">{methodLabels[tx.payment_method] || tx.payment_method}</Badge></TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold">{fmt(tx.submitted_amount)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-[10px] text-[#C24A3B]">{tx.processing_fee > 0 ? fmt(tx.processing_fee) : '—'}</TableCell>
                      <TableCell><Badge className={`border-0 text-[9px] ${statusColors[tx.status] || 'bg-[#F0F0EA] text-[#64645F]'}`}>{tx.status}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </TabsContent>

        {/* ── ERA 835 TAB ── */}
        <TabsContent value="era" className="mt-4">
          <div className="container-card" data-testid="era-documents">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">ERA 835 Documents</h3>
                <p className="text-xs text-[#8A8A85]">Electronic Remittance Advice — ANSI X12 835 format via Zelis clearinghouse</p>
              </div>
              <Button variant="outline" size="sm" onClick={fetchZelisData} className="text-xs"><RefreshCw className="h-3 w-3 mr-1" />Refresh</Button>
            </div>
            {eraDocuments.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="h-10 w-10 text-[#E2E2DF] mx-auto mb-3" />
                <p className="text-sm text-[#8A8A85]">No ERA documents generated yet</p>
                <p className="text-xs text-[#8A8A85] mt-1">Submit payments via Zelis to generate ERA 835 remittances</p>
              </div>
            ) : (
              <div className="space-y-3">
                {eraDocuments.map(era => (
                  <div key={era.id} className="p-4 bg-[#F7F7F4] rounded-lg border border-[#E2E2DF]" data-testid={`era-${era.id}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge className="bg-[#1A3636] text-white border-0 text-[10px]">{era.era_number}</Badge>
                        <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]">{era.format}</Badge>
                        <Badge className="bg-[#5C2D91] text-white border-0 text-[10px]">{era.delivery_method}</Badge>
                      </div>
                      <span className="text-[10px] text-[#8A8A85]">{new Date(era.generation_date).toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-6">
                      <div><p className="text-[10px] text-[#8A8A85]">Transactions</p><p className="text-sm font-semibold">{era.transaction_count}</p></div>
                      <div><p className="text-[10px] text-[#8A8A85]">Total Payment</p><p className="text-sm font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(era.total_payment_amount)}</p></div>
                      <div><p className="text-[10px] text-[#8A8A85]">Payer</p><p className="text-sm">{era.payer_name}</p></div>
                    </div>
                    {era.transactions && era.transactions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[#E2E2DF]">
                        <p className="text-[10px] text-[#8A8A85] mb-1">Line Items</p>
                        {era.transactions.slice(0, 5).map((t, i) => (
                          <div key={i} className="flex items-center justify-between py-1 text-[10px]">
                            <span className="font-['JetBrains_Mono'] text-[#64645F]">{t.claim_number}</span>
                            <span>{t.provider_name}</span>
                            <span className="font-['JetBrains_Mono']">Billed: {fmt(t.billed_amount)}</span>
                            <span className="font-['JetBrains_Mono'] text-[#4B6E4E]">Paid: {fmt(t.paid_amount)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
