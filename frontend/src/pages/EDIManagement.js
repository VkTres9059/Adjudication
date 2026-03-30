import { useState, useEffect, useRef } from 'react';
import { ediAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  FileText,
  Upload,
  Download,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Clock,
  ArrowRight,
  Eye,
  FileUp,
  FileDown,
  Shield,
  X,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '../components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';

export default function EDIManagement() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [txFilter, setTxFilter] = useState('all');

  // Upload/Validate state
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  // 835 state
  const [dateRange, setDateRange] = useState({ from: '', to: '' });
  const [generating835, setGenerating835] = useState(false);
  const [format835, setFormat835] = useState('x12');

  const file834Ref = useRef(null);
  const file837Ref = useRef(null);

  useEffect(() => {
    fetchTransactions();
  }, [txFilter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const res = await ediAPI.transactions(50, txFilter === 'all' ? undefined : txFilter);
      setTransactions(res.data);
    } catch { setTransactions([]); }
    finally { setLoading(false); }
  };

  // ── Validate (preview) ──
  const handleValidate = async (type) => {
    const ref = type === '834' ? file834Ref : file837Ref;
    const file = ref.current?.files?.[0];
    if (!file) { toast.error(`Select a ${type} file first`); return; }
    setValidating(true);
    setPreviewData(null);
    try {
      const res = type === '834' ? await ediAPI.validate834(file) : await ediAPI.validate837(file);
      setPreviewData({ type, ...res.data });
      toast.success(`Validated ${type}: ${res.data.member_count || res.data.claim_count || 0} records found`);
    } catch (err) { toast.error(err.response?.data?.detail || `Validation failed`); }
    finally { setValidating(false); }
  };

  // ── Upload (commit) ──
  const handleUpload = async (type) => {
    const ref = type === '834' ? file834Ref : file837Ref;
    const file = ref.current?.files?.[0];
    if (!file) { toast.error(`Select a ${type} file first`); return; }
    setUploading(true);
    setUploadResult(null);
    try {
      const res = type === '834' ? await ediAPI.upload834(file) : await ediAPI.upload837(file);
      setUploadResult({ type, ...res.data });
      if (type === '834') {
        toast.success(`834 processed: ${res.data.members_created} created, ${res.data.members_updated} updated`);
      } else {
        toast.success(`837 processed: ${res.data.claims_created} claims created`);
      }
      fetchTransactions();
      if (ref.current) ref.current.value = '';
    } catch (err) { toast.error(err.response?.data?.detail || `Upload failed`); }
    finally { setUploading(false); }
  };

  // ── 835 Generate ──
  const generate835 = async () => {
    if (!dateRange.from || !dateRange.to) { toast.error('Select date range'); return; }
    setGenerating835(true);
    try {
      const res = await ediAPI.generate835(dateRange.from, dateRange.to, format835);
      const blob = new Blob([res.data.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `835_${dateRange.from}_${dateRange.to}.${format835 === 'x12' ? 'edi' : 'txt'}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Generated 835 with ${res.data.claim_count} claims`);
      fetchTransactions();
    } catch { toast.error('Failed to generate 835'); }
    finally { setGenerating835(false); }
  };

  return (
    <div className="space-y-6" data-testid="edi-management-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']" data-testid="edi-page-title">EDI Management</h1>
          <p className="text-sm text-[#8A8A85]">X12 834 enrollment, 837 claims intake, 835 remittance generation</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchTransactions} disabled={loading} data-testid="refresh-transactions">
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />Refresh
        </Button>
      </div>

      <Tabs defaultValue="upload" className="w-full">
        <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF]">
          <TabsTrigger value="upload" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-upload">
            <FileUp className="h-3.5 w-3.5 mr-1.5" />Upload & Validate
          </TabsTrigger>
          <TabsTrigger value="generate" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-generate">
            <FileDown className="h-3.5 w-3.5 mr-1.5" />Generate 835
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-history">
            <Clock className="h-3.5 w-3.5 mr-1.5" />Transaction Log
          </TabsTrigger>
        </TabsList>

        {/* ═══ UPLOAD & VALIDATE TAB ═══ */}
        <TabsContent value="upload" className="mt-4 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* 834 Upload Card */}
            <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="upload-834-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[#1A3636]/10 rounded-lg flex items-center justify-center">
                  <Shield className="h-5 w-5 text-[#1A3636]" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">EDI 834 — Enrollment</h3>
                  <p className="text-[10px] text-[#8A8A85]">Member enrollment, terminations, and benefit changes</p>
                </div>
              </div>
              <div className="space-y-3">
                <Input ref={file834Ref} type="file" accept=".edi,.txt,.x12,.834" className="input-field text-xs" data-testid="file-834-input" />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleValidate('834')} disabled={validating} className="flex-1 text-xs" data-testid="validate-834-btn">
                    {validating ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Eye className="h-3 w-3 mr-1" />}
                    Preview
                  </Button>
                  <Button size="sm" onClick={() => handleUpload('834')} disabled={uploading} className="flex-1 btn-primary text-xs" data-testid="upload-834-btn">
                    {uploading ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Upload className="h-3 w-3 mr-1" />}
                    Upload & Process
                  </Button>
                </div>
                <p className="text-[9px] text-[#8A8A85]">Accepts X12 format (ISA envelope) or pipe-delimited</p>
              </div>
            </div>

            {/* 837 Upload Card */}
            <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="upload-837-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center">
                  <FileText className="h-5 w-5 text-[#4A6FA5]" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">EDI 837 — Claims</h3>
                  <p className="text-[10px] text-[#8A8A85]">Professional and institutional claim submissions</p>
                </div>
              </div>
              <div className="space-y-3">
                <Input ref={file837Ref} type="file" accept=".edi,.txt,.x12,.837" className="input-field text-xs" data-testid="file-837-input" />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleValidate('837')} disabled={validating} className="flex-1 text-xs" data-testid="validate-837-btn">
                    {validating ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Eye className="h-3 w-3 mr-1" />}
                    Preview
                  </Button>
                  <Button size="sm" onClick={() => handleUpload('837')} disabled={uploading} className="flex-1 btn-primary text-xs" data-testid="upload-837-btn">
                    {uploading ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Upload className="h-3 w-3 mr-1" />}
                    Upload & Process
                  </Button>
                </div>
                <p className="text-[9px] text-[#8A8A85]">Accepts X12 format (ISA envelope) or pipe-delimited</p>
              </div>
            </div>
          </div>

          {/* Preview Results */}
          {previewData && (
            <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="preview-results">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Eye className="h-4 w-4 text-[#4A6FA5]" />
                  <h3 className="text-sm font-semibold text-[#1C1C1A] font-['Outfit']">
                    Preview: {previewData.type} ({previewData.format})
                  </h3>
                  {previewData.envelope && (
                    <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]">
                      Control: {previewData.envelope.control_number}
                    </Badge>
                  )}
                </div>
                <Button variant="ghost" size="sm" onClick={() => setPreviewData(null)} className="text-xs">
                  <X className="h-3 w-3" />
                </Button>
              </div>

              {/* Envelope info */}
              {previewData.envelope && (
                <div className="grid grid-cols-4 gap-3 mb-4">
                  <div className="bg-[#F7F7F4] rounded-lg p-2.5 h-[52px]">
                    <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Sender</p>
                    <p className="text-xs font-medium font-['JetBrains_Mono']">{previewData.envelope.sender_id}</p>
                  </div>
                  <div className="bg-[#F7F7F4] rounded-lg p-2.5 h-[52px]">
                    <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Receiver</p>
                    <p className="text-xs font-medium font-['JetBrains_Mono']">{previewData.envelope.receiver_id}</p>
                  </div>
                  <div className="bg-[#F7F7F4] rounded-lg p-2.5 h-[52px]">
                    <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Date</p>
                    <p className="text-xs font-medium tabular-nums">{previewData.envelope.date}</p>
                  </div>
                  <div className="bg-[#F7F7F4] rounded-lg p-2.5 h-[52px]">
                    <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Segments</p>
                    <p className="text-xs font-medium tabular-nums">{previewData.segment_count}</p>
                  </div>
                </div>
              )}

              {/* Errors */}
              {previewData.errors?.length > 0 && (
                <div className="bg-[#FFF5F5] border border-[#C24A3B]/20 rounded-lg p-3 mb-4">
                  <div className="flex items-center gap-1.5 mb-1"><AlertTriangle className="h-3.5 w-3.5 text-[#C24A3B]" /><span className="text-xs font-medium text-[#C24A3B]">{previewData.errors.length} Errors</span></div>
                  {previewData.errors.slice(0, 5).map((e, i) => (
                    <p key={i} className="text-[10px] text-[#C24A3B] ml-5">{e.error || e}</p>
                  ))}
                </div>
              )}

              {/* Member preview (834) */}
              {previewData.members?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-[#64645F] mb-2">{previewData.member_count} Members</p>
                  <Table>
                    <TableHeader><TableRow className="border-[#E2E2DF]">
                      <TableHead>Member ID</TableHead><TableHead>Name</TableHead><TableHead>DOB</TableHead>
                      <TableHead>Group</TableHead><TableHead>Plan</TableHead><TableHead>Effective</TableHead>
                      <TableHead>Action</TableHead><TableHead>Type</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {previewData.members.map((m, i) => (
                        <TableRow key={i} className="h-[40px]" data-testid={`preview-member-${i}`}>
                          <TableCell className="font-['JetBrains_Mono'] text-xs">{m.member_id}</TableCell>
                          <TableCell className="text-xs">{m.first_name} {m.last_name}</TableCell>
                          <TableCell className="text-xs tabular-nums">{m.dob}</TableCell>
                          <TableCell className="text-xs">{m.group_id}</TableCell>
                          <TableCell className="text-xs">{m.plan_id}</TableCell>
                          <TableCell className="text-xs tabular-nums">{m.effective_date}</TableCell>
                          <TableCell>
                            <Badge className={
                              m.maintenance_type === 'addition' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' :
                              m.maintenance_type === 'cancellation' || m.maintenance_type === 'termination' ? 'bg-[#C24A3B] text-white border-0 text-[9px]' :
                              m.maintenance_type === 'reinstatement' ? 'bg-[#4A6FA5] text-white border-0 text-[9px]' :
                              'bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]'
                            }>{m.maintenance_type}</Badge>
                          </TableCell>
                          <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]">{m.coverage_type || m.relationship}</Badge></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* Claim preview (837) */}
              {previewData.claims?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-[#64645F] mb-2">{previewData.claim_count} Claims</p>
                  <Table>
                    <TableHeader><TableRow className="border-[#E2E2DF]">
                      <TableHead>Member ID</TableHead><TableHead>Provider</TableHead><TableHead>NPI</TableHead>
                      <TableHead>Service Date</TableHead><TableHead>Dx Codes</TableHead>
                      <TableHead className="text-right">Billed</TableHead><TableHead>Lines</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {previewData.claims.map((c, i) => (
                        <TableRow key={i} className="h-[40px]" data-testid={`preview-claim-${i}`}>
                          <TableCell className="font-['JetBrains_Mono'] text-xs">{c.member_id}</TableCell>
                          <TableCell className="text-xs truncate max-w-[140px]">{c.provider_name}</TableCell>
                          <TableCell className="font-['JetBrains_Mono'] text-xs">{c.provider_npi}</TableCell>
                          <TableCell className="text-xs tabular-nums">{c.service_date_from}</TableCell>
                          <TableCell className="text-xs font-['JetBrains_Mono']">{c.diagnosis_codes?.join(', ')}</TableCell>
                          <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">${c.total_billed?.toFixed(2)}</TableCell>
                          <TableCell className="text-xs tabular-nums">{c.service_line_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}

          {/* Upload Result */}
          {uploadResult && (
            <div className="bg-[#F0F7F1] border border-[#4B6E4E]/20 rounded-xl p-5" data-testid="upload-result">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="h-4 w-4 text-[#4B6E4E]" />
                <h3 className="text-sm font-semibold text-[#4B6E4E]">Upload Complete — {uploadResult.type}</h3>
                {uploadResult.envelope && (
                  <Badge className="bg-[#4B6E4E] text-white border-0 text-[9px]">Control: {uploadResult.envelope.control_number}</Badge>
                )}
                <Button variant="ghost" size="sm" onClick={() => setUploadResult(null)} className="ml-auto text-xs">
                  <X className="h-3 w-3" />
                </Button>
              </div>
              <div className="grid grid-cols-4 gap-3">
                {uploadResult.type === '834' ? (
                  <>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Created</p>
                      <p className="text-lg font-bold tabular-nums text-[#4B6E4E]">{uploadResult.members_created}</p>
                    </div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Updated</p>
                      <p className="text-lg font-bold tabular-nums text-[#4A6FA5]">{uploadResult.members_updated}</p>
                    </div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Terminated</p>
                      <p className="text-lg font-bold tabular-nums text-[#C24A3B]">{uploadResult.members_terminated}</p>
                    </div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Errors</p>
                      <p className="text-lg font-bold tabular-nums text-[#C9862B]">{uploadResult.errors?.length || 0}</p>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Claims Created</p>
                      <p className="text-lg font-bold tabular-nums text-[#4B6E4E]">{uploadResult.claims_created}</p>
                    </div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Segments</p>
                      <p className="text-lg font-bold tabular-nums">{uploadResult.segment_count || 0}</p>
                    </div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px] col-span-2">
                      <p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Errors</p>
                      <p className="text-lg font-bold tabular-nums text-[#C9862B]">{uploadResult.errors?.length || 0}</p>
                    </div>
                  </>
                )}
              </div>
              {uploadResult.errors?.length > 0 && (
                <div className="mt-3 bg-white rounded-lg p-3 border border-[#E2E2DF]">
                  {uploadResult.errors.map((e, i) => <p key={i} className="text-[10px] text-[#C24A3B]">{e}</p>)}
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* ═══ GENERATE 835 TAB ═══ */}
        <TabsContent value="generate" className="mt-4">
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="generate-835-section">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 bg-[#C9862B]/10 rounded-lg flex items-center justify-center">
                <FileDown className="h-5 w-5 text-[#C9862B]" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Generate EDI 835 — Remittance Advice</h3>
                <p className="text-[10px] text-[#8A8A85]">Generate payment/remittance file for approved claims in a date range</p>
              </div>
            </div>

            <div className="flex items-end gap-4 max-w-2xl">
              <div className="space-y-1.5 flex-1">
                <Label className="text-xs">Adjudicated From</Label>
                <Input
                  type="date"
                  value={dateRange.from}
                  onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
                  className="input-field"
                  data-testid="835-date-from"
                />
              </div>
              <div className="space-y-1.5 flex-1">
                <Label className="text-xs">Adjudicated To</Label>
                <Input
                  type="date"
                  value={dateRange.to}
                  onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
                  className="input-field"
                  data-testid="835-date-to"
                />
              </div>
              <div className="space-y-1.5 w-[140px]">
                <Label className="text-xs">Format</Label>
                <Select value={format835} onValueChange={setFormat835}>
                  <SelectTrigger className="input-field" data-testid="835-format-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="x12">X12 835</SelectItem>
                    <SelectItem value="pipe">Pipe-delimited</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={generate835} disabled={generating835} className="btn-primary" data-testid="generate-835-btn">
                {generating835 ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                Generate 835
              </Button>
            </div>

            <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="bg-[#F7F7F4] rounded-lg p-4 border border-[#E2E2DF]">
                <p className="font-medium text-[#1C1C1A] mb-1">X12 835 Format</p>
                <p className="text-[#64645F]">Compliant X12 remittance with ISA/GS/ST envelopes, BPR financial info, CLP claim payments, SVC service lines, CAS adjustments, AMT allowed amounts.</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4 border border-[#E2E2DF]">
                <p className="font-medium text-[#1C1C1A] mb-1">Adjustment Codes</p>
                <p className="text-[#64645F]">CO-45 (contractual obligation), PR-1 (deductible), PR-2 (coinsurance), PR-3 (copay). Service-level CAS and AMT segments for each line.</p>
              </div>
              <div className="bg-[#F7F7F4] rounded-lg p-4 border border-[#E2E2DF]">
                <p className="font-medium text-[#1C1C1A] mb-1">Pipe-Delimited</p>
                <p className="text-[#64645F]">Simple flat format: ClaimNumber|MemberID|ProviderNPI|Billed|Allowed|Paid|MemberResp. Useful for integration testing.</p>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* ═══ TRANSACTION LOG TAB ═══ */}
        <TabsContent value="history" className="mt-4">
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="transaction-log">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#1A3636]/10 rounded-lg flex items-center justify-center">
                  <Clock className="h-5 w-5 text-[#1A3636]" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Transaction Log</h3>
                  <p className="text-[10px] text-[#8A8A85]">Every EDI file processed through the system</p>
                </div>
              </div>
              <Select value={txFilter} onValueChange={setTxFilter}>
                <SelectTrigger className="w-[140px] input-field" data-testid="tx-filter">
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="834">834 Only</SelectItem>
                  <SelectItem value="837">837 Only</SelectItem>
                  <SelectItem value="835">835 Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {transactions.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-8 text-center">
                <Clock className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" />
                <p className="text-sm text-[#8A8A85]">No EDI transactions recorded yet</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-[#E2E2DF]">
                    <TableHead>Type</TableHead>
                    <TableHead>Filename</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Control #</TableHead>
                    <TableHead className="text-right">Records</TableHead>
                    <TableHead className="text-right">Segments</TableHead>
                    <TableHead className="text-right">Errors</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((tx) => (
                    <TableRow key={tx.id} className="table-row h-[44px]" data-testid={`tx-row-${tx.id}`}>
                      <TableCell>
                        <Badge className={
                          tx.type === '834' ? 'bg-[#1A3636] text-white border-0 text-[10px]' :
                          tx.type === '837' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                          'bg-[#C9862B] text-white border-0 text-[10px]'
                        }>{tx.type}</Badge>
                      </TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono'] truncate max-w-[180px]">{tx.filename}</TableCell>
                      <TableCell>
                        <Badge className={
                          tx.status === 'success' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' :
                          tx.status === 'partial' ? 'bg-[#C9862B] text-white border-0 text-[9px]' :
                          'bg-[#C24A3B] text-white border-0 text-[9px]'
                        }>{tx.status}</Badge>
                      </TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-[10px]">{tx.envelope?.control_number || '—'}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{tx.record_count}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{tx.segment_count || '—'}</TableCell>
                      <TableCell className="text-right">
                        <span className={`font-['JetBrains_Mono'] text-xs tabular-nums ${tx.error_count > 0 ? 'text-[#C24A3B] font-bold' : 'text-[#8A8A85]'}`}>
                          {tx.error_count}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs tabular-nums text-[#8A8A85]">{new Date(tx.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
