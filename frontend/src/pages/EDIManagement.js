import { useState, useEffect, useRef } from 'react';
import { ediAPI, settingsAPI, sftpAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  FileText,
  Upload,
  Download,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Clock,
  Eye,
  FileUp,
  FileDown,
  Shield,
  X,
  Send,
  ArrowRight,
  Server,
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
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../components/ui/dialog';

export default function EDIManagement() {
  const [transactions, setTransactions] = useState([]);
  const [transmissions, setTransmissions] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [intakeLogs, setIntakeLogs] = useState([]);
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

  // Export state
  const [exporting834, setExporting834] = useState(false);
  const [exportingAuth, setExportingAuth] = useState(false);
  const [exportVendor834, setExportVendor834] = useState('');
  const [exportFormat834, setExportFormat834] = useState('hipaa_5010');
  const [exportVendorAuth, setExportVendorAuth] = useState('');
  const [exportFormatAuth, setExportFormatAuth] = useState('csv');
  const [authDateRange, setAuthDateRange] = useState({ from: '', to: '' });

  // Preview modal
  const [previewModal, setPreviewModal] = useState(null);

  const file834Ref = useRef(null);
  const file837Ref = useRef(null);

  useEffect(() => {
    fetchAll();
  }, []);

  useEffect(() => {
    fetchTransactions();
  }, [txFilter]);

  const fetchAll = async () => {
    setLoading(true);
    await Promise.all([fetchTransactions(), fetchTransmissions(), fetchVendors(), fetchIntakeLogs()]);
    setLoading(false);
  };

  const fetchTransactions = async () => {
    try {
      const res = await ediAPI.transactions(50, txFilter === 'all' ? undefined : txFilter);
      setTransactions(res.data);
    } catch { setTransactions([]); }
  };

  const fetchTransmissions = async () => {
    try {
      const res = await ediAPI.transmissions(50);
      setTransmissions(res.data);
    } catch { setTransmissions([]); }
  };

  const fetchVendors = async () => {
    try {
      const res = await settingsAPI.getVendors();
      setVendors(res.data);
    } catch { setVendors([]); }
  };

  const fetchIntakeLogs = async () => {
    try {
      const res = await sftpAPI.intakeLogs(50);
      setIntakeLogs(res.data);
    } catch { setIntakeLogs([]); }
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
      toast.success(`Validated ${type}: ${res.data.member_count || res.data.claim_count || 0} records`);
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
      toast.success(type === '834'
        ? `834: ${res.data.members_created} created, ${res.data.members_updated} updated`
        : `837: ${res.data.claims_created} claims created`
      );
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
      downloadFile(res.data.content, `835_${dateRange.from}_${dateRange.to}.${format835 === 'x12' ? 'edi' : 'txt'}`);
      toast.success(`835: ${res.data.claim_count} claims`);
      fetchTransactions();
    } catch { toast.error('Failed to generate 835'); }
    finally { setGenerating835(false); }
  };

  // ── Export 834 Feed ──
  const handleExport834 = async (preview = false) => {
    setExporting834(true);
    try {
      const res = await ediAPI.export834(exportVendor834 || undefined, exportFormat834);
      if (preview) {
        setPreviewModal({ title: `834 Export Preview — ${res.data.vendor_name}`, ...res.data });
      } else {
        downloadFile(res.data.content, res.data.filename);
        toast.success(`834 exported: ${res.data.adds} adds, ${res.data.terms} terms`);
      }
      fetchTransmissions();
    } catch (err) { toast.error(err.response?.data?.detail || 'Export failed'); }
    finally { setExporting834(false); }
  };

  // ── Export Auth Feed ──
  const handleExportAuth = async () => {
    setExportingAuth(true);
    try {
      const res = await ediAPI.exportAuthFeed(
        exportVendorAuth || undefined, exportFormatAuth,
        authDateRange.from || undefined, authDateRange.to || undefined
      );
      downloadFile(res.data.content, res.data.filename);
      toast.success(`Auth feed: ${res.data.auth_count} authorizations`);
      fetchTransmissions();
    } catch (err) { toast.error(err.response?.data?.detail || 'Export failed'); }
    finally { setExportingAuth(false); }
  };

  const downloadFile = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="edi-management-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']" data-testid="edi-page-title">EDI Management</h1>
          <p className="text-sm text-[#8A8A85]">X12 834/837/835 interchange, export feeds, and transmission audit</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAll} disabled={loading} data-testid="refresh-all">
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />Refresh
        </Button>
      </div>

      <Tabs defaultValue="upload" className="w-full">
        <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF]">
          <TabsTrigger value="upload" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-upload">
            <FileUp className="h-3.5 w-3.5 mr-1.5" />Upload & Validate
          </TabsTrigger>
          <TabsTrigger value="export" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-export">
            <Send className="h-3.5 w-3.5 mr-1.5" />Export Feeds
          </TabsTrigger>
          <TabsTrigger value="generate" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-generate">
            <FileDown className="h-3.5 w-3.5 mr-1.5" />Generate 835
          </TabsTrigger>
          <TabsTrigger value="transmissions" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-transmissions">
            <ArrowRight className="h-3.5 w-3.5 mr-1.5" />Transmission Log
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-history">
            <Clock className="h-3.5 w-3.5 mr-1.5" />Inbound Log
          </TabsTrigger>
          <TabsTrigger value="intake" className="data-[state=active]:bg-white text-sm" data-testid="edi-tab-intake">
            <Server className="h-3.5 w-3.5 mr-1.5" />SFTP Intake
          </TabsTrigger>
        </TabsList>

        {/* ═══ UPLOAD TAB ═══ */}
        <TabsContent value="upload" className="mt-4 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* 834 Card */}
            <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="upload-834-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[#1A3636]/10 rounded-lg flex items-center justify-center"><Shield className="h-5 w-5 text-[#1A3636]" /></div>
                <div><h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">EDI 834 — Enrollment</h3><p className="text-[10px] text-[#8A8A85]">Member enrollment, terminations, benefit changes</p></div>
              </div>
              <div className="space-y-3">
                <Input ref={file834Ref} type="file" accept=".edi,.txt,.x12,.834" className="input-field text-xs" data-testid="file-834-input" />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleValidate('834')} disabled={validating} className="flex-1 text-xs" data-testid="validate-834-btn">
                    {validating ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Eye className="h-3 w-3 mr-1" />}Preview
                  </Button>
                  <Button size="sm" onClick={() => handleUpload('834')} disabled={uploading} className="flex-1 btn-primary text-xs" data-testid="upload-834-btn">
                    {uploading ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Upload className="h-3 w-3 mr-1" />}Upload & Process
                  </Button>
                </div>
              </div>
            </div>
            {/* 837 Card */}
            <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="upload-837-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center"><FileText className="h-5 w-5 text-[#4A6FA5]" /></div>
                <div><h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">EDI 837 — Claims</h3><p className="text-[10px] text-[#8A8A85]">Professional and institutional claims</p></div>
              </div>
              <div className="space-y-3">
                <Input ref={file837Ref} type="file" accept=".edi,.txt,.x12,.837" className="input-field text-xs" data-testid="file-837-input" />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleValidate('837')} disabled={validating} className="flex-1 text-xs" data-testid="validate-837-btn">
                    {validating ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Eye className="h-3 w-3 mr-1" />}Preview
                  </Button>
                  <Button size="sm" onClick={() => handleUpload('837')} disabled={uploading} className="flex-1 btn-primary text-xs" data-testid="upload-837-btn">
                    {uploading ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Upload className="h-3 w-3 mr-1" />}Upload & Process
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Inline Preview */}
          {previewData && (
            <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="preview-results">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Eye className="h-4 w-4 text-[#4A6FA5]" />
                  <h3 className="text-sm font-semibold text-[#1C1C1A]">Preview: {previewData.type} ({previewData.format})</h3>
                  {previewData.envelope && <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]">Control: {previewData.envelope.control_number}</Badge>}
                </div>
                <Button variant="ghost" size="sm" onClick={() => setPreviewData(null)}><X className="h-3 w-3" /></Button>
              </div>
              {previewData.envelope && (
                <div className="grid grid-cols-4 gap-3 mb-4">
                  {[['Sender', previewData.envelope.sender_id], ['Receiver', previewData.envelope.receiver_id], ['Date', previewData.envelope.date], ['Segments', previewData.segment_count]].map(([l, v]) => (
                    <div key={l} className="bg-[#F7F7F4] rounded-lg p-2.5 h-[52px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">{l}</p><p className="text-xs font-medium font-['JetBrains_Mono']">{v}</p></div>
                  ))}
                </div>
              )}
              {previewData.errors?.length > 0 && (
                <div className="bg-[#FFF5F5] border border-[#C24A3B]/20 rounded-lg p-3 mb-4">
                  <div className="flex items-center gap-1.5 mb-1"><AlertTriangle className="h-3.5 w-3.5 text-[#C24A3B]" /><span className="text-xs font-medium text-[#C24A3B]">{previewData.errors.length} Errors</span></div>
                  {previewData.errors.slice(0, 5).map((e, i) => <p key={i} className="text-[10px] text-[#C24A3B] ml-5">{e.error || e}</p>)}
                </div>
              )}
              {previewData.members?.length > 0 && (
                <Table><TableHeader><TableRow className="border-[#E2E2DF]"><TableHead>Member ID</TableHead><TableHead>Name</TableHead><TableHead>DOB</TableHead><TableHead>Group</TableHead><TableHead>Effective</TableHead><TableHead>Action</TableHead></TableRow></TableHeader>
                  <TableBody>{previewData.members.map((m, i) => (
                    <TableRow key={i} className="h-[40px]"><TableCell className="font-['JetBrains_Mono'] text-xs">{m.member_id}</TableCell><TableCell className="text-xs">{m.first_name} {m.last_name}</TableCell><TableCell className="text-xs tabular-nums">{m.dob}</TableCell><TableCell className="text-xs">{m.group_id}</TableCell><TableCell className="text-xs tabular-nums">{m.effective_date}</TableCell>
                      <TableCell><Badge className={m.maintenance_type === 'addition' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : m.maintenance_type?.includes('cancel') || m.maintenance_type?.includes('term') ? 'bg-[#C24A3B] text-white border-0 text-[9px]' : 'bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]'}>{m.maintenance_type}</Badge></TableCell></TableRow>
                  ))}</TableBody></Table>
              )}
              {previewData.claims?.length > 0 && (
                <Table><TableHeader><TableRow className="border-[#E2E2DF]"><TableHead>Member</TableHead><TableHead>Provider</TableHead><TableHead>Date</TableHead><TableHead>Dx</TableHead><TableHead className="text-right">Billed</TableHead><TableHead>Lines</TableHead></TableRow></TableHeader>
                  <TableBody>{previewData.claims.map((c, i) => (
                    <TableRow key={i} className="h-[40px]"><TableCell className="font-['JetBrains_Mono'] text-xs">{c.member_id}</TableCell><TableCell className="text-xs truncate max-w-[140px]">{c.provider_name}</TableCell><TableCell className="text-xs tabular-nums">{c.service_date_from}</TableCell><TableCell className="text-xs font-['JetBrains_Mono']">{c.diagnosis_codes?.join(', ')}</TableCell><TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">${c.total_billed?.toFixed(2)}</TableCell><TableCell className="text-xs">{c.service_line_count}</TableCell></TableRow>
                  ))}</TableBody></Table>
              )}
            </div>
          )}

          {/* Upload Result */}
          {uploadResult && (
            <div className="bg-[#F0F7F1] border border-[#4B6E4E]/20 rounded-xl p-5" data-testid="upload-result">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="h-4 w-4 text-[#4B6E4E]" />
                <h3 className="text-sm font-semibold text-[#4B6E4E]">Upload Complete — {uploadResult.type}</h3>
                <Button variant="ghost" size="sm" onClick={() => setUploadResult(null)} className="ml-auto"><X className="h-3 w-3" /></Button>
              </div>
              <div className="grid grid-cols-4 gap-3">
                {uploadResult.type === '834' ? (
                  <>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Created</p><p className="text-lg font-bold tabular-nums text-[#4B6E4E]">{uploadResult.members_created}</p></div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Updated</p><p className="text-lg font-bold tabular-nums text-[#4A6FA5]">{uploadResult.members_updated}</p></div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Terminated</p><p className="text-lg font-bold tabular-nums text-[#C24A3B]">{uploadResult.members_terminated}</p></div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Errors</p><p className="text-lg font-bold tabular-nums text-[#C9862B]">{uploadResult.errors?.length || 0}</p></div>
                  </>
                ) : (
                  <>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Claims Created</p><p className="text-lg font-bold tabular-nums text-[#4B6E4E]">{uploadResult.claims_created}</p></div>
                    <div className="bg-white rounded-lg p-2.5 border border-[#E2E2DF] h-[52px] col-span-3"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Errors</p><p className="text-lg font-bold tabular-nums text-[#C9862B]">{uploadResult.errors?.length || 0}</p></div>
                  </>
                )}
              </div>
            </div>
          )}
        </TabsContent>

        {/* ═══ EXPORT FEEDS TAB ═══ */}
        <TabsContent value="export" className="mt-4 space-y-5">
          {/* 834 Export */}
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="export-834-section">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-[#1A3636]/10 rounded-lg flex items-center justify-center"><Shield className="h-5 w-5 text-[#1A3636]" /></div>
              <div>
                <h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Export 834 Enrollment Feed</h3>
                <p className="text-[10px] text-[#8A8A85]">Full enrollment feed — Active members = Add (021), below-threshold = Term (024)</p>
              </div>
            </div>
            <div className="flex items-end gap-4 max-w-3xl">
              <div className="space-y-1.5 flex-1">
                <Label className="text-xs">Destination Vendor</Label>
                <Select value={exportVendor834} onValueChange={setExportVendor834}>
                  <SelectTrigger className="input-field" data-testid="export-834-vendor"><SelectValue placeholder="Manual Export" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Manual Export</SelectItem>
                    {vendors.filter(v => v.feed_types?.includes('834')).map(v => (
                      <SelectItem key={v.id} value={v.id}>{v.name} ({v.format})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5 w-[180px]">
                <Label className="text-xs">Format</Label>
                <Select value={exportFormat834} onValueChange={setExportFormat834}>
                  <SelectTrigger className="input-field" data-testid="export-834-format"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hipaa_5010">HIPAA 5010 X12</SelectItem>
                    <SelectItem value="csv">Custom CSV</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button variant="outline" size="sm" onClick={() => handleExport834(true)} disabled={exporting834} className="text-xs" data-testid="preview-834-export-btn">
                {exporting834 ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Eye className="h-3 w-3 mr-1" />}Preview
              </Button>
              <Button size="sm" onClick={() => handleExport834(false)} disabled={exporting834} className="btn-primary text-xs" data-testid="export-834-btn">
                {exporting834 ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Download className="h-3 w-3 mr-1" />}Export & Download
              </Button>
            </div>
          </div>

          {/* Auth Feed Export */}
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="export-auth-section">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-[#5C2D91]/10 rounded-lg flex items-center justify-center"><FileText className="h-5 w-5 text-[#5C2D91]" /></div>
              <div>
                <h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Export Authorization (278) Feed</h3>
                <p className="text-[10px] text-[#8A8A85]">Auth records generated when examiners approve held claims — for PBM/TPA partners</p>
              </div>
            </div>
            <div className="flex items-end gap-4 max-w-4xl flex-wrap">
              <div className="space-y-1.5 flex-1 min-w-[160px]">
                <Label className="text-xs">Vendor</Label>
                <Select value={exportVendorAuth} onValueChange={setExportVendorAuth}>
                  <SelectTrigger className="input-field" data-testid="export-auth-vendor"><SelectValue placeholder="Manual Export" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Manual Export</SelectItem>
                    {vendors.filter(v => v.feed_types?.includes('278')).map(v => (
                      <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5 w-[150px]">
                <Label className="text-xs">Format</Label>
                <Select value={exportFormatAuth} onValueChange={setExportFormatAuth}>
                  <SelectTrigger className="input-field" data-testid="export-auth-format"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hipaa_5010">HIPAA 5010</SelectItem>
                    <SelectItem value="csv">Custom CSV</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5 w-[130px]">
                <Label className="text-xs">From</Label>
                <Input type="date" value={authDateRange.from} onChange={(e) => setAuthDateRange({...authDateRange, from: e.target.value})} className="input-field" data-testid="auth-date-from" />
              </div>
              <div className="space-y-1.5 w-[130px]">
                <Label className="text-xs">To</Label>
                <Input type="date" value={authDateRange.to} onChange={(e) => setAuthDateRange({...authDateRange, to: e.target.value})} className="input-field" data-testid="auth-date-to" />
              </div>
              <Button size="sm" onClick={handleExportAuth} disabled={exportingAuth} className="bg-[#5C2D91] hover:bg-[#4a2475] text-white text-xs" data-testid="export-auth-btn">
                {exportingAuth ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Download className="h-3 w-3 mr-1" />}Export Auth Feed
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* ═══ GENERATE 835 TAB ═══ */}
        <TabsContent value="generate" className="mt-4">
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="generate-835-section">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 bg-[#C9862B]/10 rounded-lg flex items-center justify-center"><FileDown className="h-5 w-5 text-[#C9862B]" /></div>
              <div><h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Generate EDI 835 — Remittance Advice</h3><p className="text-[10px] text-[#8A8A85]">Payment/remittance for approved claims in date range</p></div>
            </div>
            <div className="flex items-end gap-4 max-w-2xl">
              <div className="space-y-1.5 flex-1"><Label className="text-xs">From</Label><Input type="date" value={dateRange.from} onChange={(e) => setDateRange({...dateRange, from: e.target.value})} className="input-field" data-testid="835-date-from" /></div>
              <div className="space-y-1.5 flex-1"><Label className="text-xs">To</Label><Input type="date" value={dateRange.to} onChange={(e) => setDateRange({...dateRange, to: e.target.value})} className="input-field" data-testid="835-date-to" /></div>
              <div className="space-y-1.5 w-[140px]"><Label className="text-xs">Format</Label>
                <Select value={format835} onValueChange={setFormat835}><SelectTrigger className="input-field" data-testid="835-format-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="x12">X12 835</SelectItem><SelectItem value="pipe">Pipe-delimited</SelectItem></SelectContent></Select>
              </div>
              <Button onClick={generate835} disabled={generating835} className="btn-primary" data-testid="generate-835-btn">
                {generating835 ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}Generate 835
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* ═══ TRANSMISSION LOG TAB ═══ */}
        <TabsContent value="transmissions" className="mt-4">
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="transmission-log">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center"><Send className="h-5 w-5 text-[#4A6FA5]" /></div>
              <div><h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Transmission Log</h3><p className="text-[10px] text-[#8A8A85]">Every outbound feed: date, filename, destination, status</p></div>
              <Button variant="outline" size="sm" onClick={fetchTransmissions} className="ml-auto text-xs" data-testid="refresh-transmissions"><RefreshCw className="h-3 w-3 mr-1" />Refresh</Button>
            </div>

            {transmissions.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-8 text-center"><Send className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" /><p className="text-sm text-[#8A8A85]">No outbound transmissions yet</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]">
                  <TableHead>Feed Type</TableHead><TableHead>Filename</TableHead><TableHead>Destination</TableHead>
                  <TableHead>Status</TableHead><TableHead className="text-right">Records</TableHead><TableHead>Details</TableHead><TableHead>Date</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {transmissions.map((tx) => (
                    <TableRow key={tx.id} className="table-row h-[44px]" data-testid={`transmission-row-${tx.id}`}>
                      <TableCell><Badge className={
                        tx.feed_type === '834_export' ? 'bg-[#1A3636] text-white border-0 text-[10px]' :
                        tx.feed_type === '278_auth' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                        'bg-[#C9862B] text-white border-0 text-[10px]'
                      }>{tx.feed_type}</Badge></TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono'] truncate max-w-[200px]">{tx.filename}</TableCell>
                      <TableCell className="text-xs">{tx.vendor_name}</TableCell>
                      <TableCell><Badge className={tx.status === 'success' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : 'bg-[#C24A3B] text-white border-0 text-[9px]'}>{tx.status}</Badge></TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{tx.record_count}</TableCell>
                      <TableCell className="text-[10px] text-[#8A8A85]">
                        {tx.details?.adds != null && <span>+{tx.details.adds} </span>}
                        {tx.details?.terms != null && <span className="text-[#C24A3B]">-{tx.details.terms} </span>}
                        {tx.details?.format && <span>{tx.details.format}</span>}
                      </TableCell>
                      <TableCell className="text-xs tabular-nums text-[#8A8A85]">{new Date(tx.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* ═══ INBOUND LOG TAB ═══ */}
        <TabsContent value="history" className="mt-4">
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="transaction-log">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#1A3636]/10 rounded-lg flex items-center justify-center"><Clock className="h-5 w-5 text-[#1A3636]" /></div>
                <div><h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">Inbound Transaction Log</h3><p className="text-[10px] text-[#8A8A85]">Every inbound EDI file processed</p></div>
              </div>
              <Select value={txFilter} onValueChange={setTxFilter}>
                <SelectTrigger className="w-[140px] input-field" data-testid="tx-filter"><SelectValue placeholder="All types" /></SelectTrigger>
                <SelectContent><SelectItem value="all">All Types</SelectItem><SelectItem value="834">834</SelectItem><SelectItem value="837">837</SelectItem><SelectItem value="835">835</SelectItem></SelectContent>
              </Select>
            </div>
            {transactions.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-8 text-center"><Clock className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" /><p className="text-sm text-[#8A8A85]">No inbound transactions</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]"><TableHead>Type</TableHead><TableHead>Filename</TableHead><TableHead>Status</TableHead><TableHead>Control #</TableHead><TableHead className="text-right">Records</TableHead><TableHead className="text-right">Segments</TableHead><TableHead className="text-right">Errors</TableHead><TableHead>Date</TableHead></TableRow></TableHeader>
                <TableBody>
                  {transactions.map((tx) => (
                    <TableRow key={tx.id} className="table-row h-[44px]" data-testid={`tx-row-${tx.id}`}>
                      <TableCell><Badge className={tx.type === '834' ? 'bg-[#1A3636] text-white border-0 text-[10px]' : tx.type === '837' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' : 'bg-[#C9862B] text-white border-0 text-[10px]'}>{tx.type}</Badge></TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono'] truncate max-w-[180px]">{tx.filename}</TableCell>
                      <TableCell><Badge className={tx.status === 'success' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' : tx.status === 'partial' ? 'bg-[#C9862B] text-white border-0 text-[9px]' : 'bg-[#C24A3B] text-white border-0 text-[9px]'}>{tx.status}</Badge></TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-[10px]">{tx.envelope?.control_number || '—'}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{tx.record_count}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{tx.segment_count || '—'}</TableCell>
                      <TableCell className="text-right"><span className={`font-['JetBrains_Mono'] text-xs tabular-nums ${tx.error_count > 0 ? 'text-[#C24A3B] font-bold' : 'text-[#8A8A85]'}`}>{tx.error_count}</span></TableCell>
                      <TableCell className="text-xs tabular-nums text-[#8A8A85]">{new Date(tx.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* ═══ SFTP INTAKE HISTORY TAB ═══ */}
        <TabsContent value="intake" className="mt-4">
          <div className="bg-white rounded-xl border border-[#E2E2DF] p-5" data-testid="intake-history-log">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#5C2D91]/10 rounded-lg flex items-center justify-center"><Server className="h-5 w-5 text-[#5C2D91]" /></div>
                <div><h3 className="text-base font-semibold text-[#1C1C1A] font-['Outfit']">SFTP Intake History</h3><p className="text-[10px] text-[#8A8A85]">Automated file ingestion: date, filename, records processed, status</p></div>
              </div>
              <Button variant="outline" size="sm" onClick={fetchIntakeLogs} className="text-xs" data-testid="refresh-intake-logs"><RefreshCw className="h-3 w-3 mr-1" />Refresh</Button>
            </div>
            {intakeLogs.length === 0 ? (
              <div className="bg-[#F7F7F4] rounded-lg p-8 text-center"><Server className="h-8 w-8 text-[#8A8A85] mx-auto mb-2" /><p className="text-sm text-[#8A8A85]">No SFTP intake runs yet. Configure schedules in Settings &rarr; SFTP Scheduler.</p></div>
            ) : (
              <Table>
                <TableHeader><TableRow className="border-[#E2E2DF]">
                  <TableHead>Date</TableHead><TableHead>Schedule</TableHead><TableHead>Connection</TableHead><TableHead>File Name</TableHead><TableHead>Route</TableHead><TableHead className="text-right">Records</TableHead><TableHead>Status</TableHead><TableHead>Error</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {intakeLogs.map((log) => (
                    <TableRow key={log.id} className="table-row h-[44px]" data-testid={`intake-row-${log.id}`}>
                      <TableCell className="text-xs tabular-nums text-[#8A8A85]">{new Date(log.started_at).toLocaleString()}</TableCell>
                      <TableCell className="text-xs">{log.schedule_name}</TableCell>
                      <TableCell className="text-xs">{log.connection_name}</TableCell>
                      <TableCell className="text-xs font-['JetBrains_Mono'] truncate max-w-[200px]">{log.filename || '—'}</TableCell>
                      <TableCell><Badge className={
                        log.route_type === '834' ? 'bg-[#1A3636] text-white border-0 text-[10px]' :
                        log.route_type === 'work_report' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                        'bg-[#4A6FA5] text-white border-0 text-[10px]'
                      }>{log.route_type === '834' ? 'Enrollment' : log.route_type === 'work_report' ? 'Hour Bank' : 'Adjudication'}</Badge></TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs tabular-nums">{log.records_processed}</TableCell>
                      <TableCell><Badge className={
                        log.status === 'success' ? 'bg-[#4B6E4E] text-white border-0 text-[9px]' :
                        log.status === 'partial' ? 'bg-[#C9862B] text-white border-0 text-[9px]' :
                        log.status === 'running' ? 'bg-[#4A6FA5] text-white border-0 text-[9px]' :
                        'bg-[#C24A3B] text-white border-0 text-[9px]'
                      }>{log.status}</Badge></TableCell>
                      <TableCell className="text-[10px] text-[#C24A3B] truncate max-w-[200px]">{log.error_message || '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* ═══ PREVIEW MODAL (non-shifting) ═══ */}
      <Dialog open={!!previewModal} onOpenChange={(open) => { if (!open) setPreviewModal(null); }}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col" data-testid="export-preview-modal">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">{previewModal?.title || 'Export Preview'}</DialogTitle>
          </DialogHeader>
          {previewModal && (
            <div className="flex-1 overflow-y-auto space-y-4 pt-2">
              {/* Summary cards — fixed height */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-[#F7F7F4] rounded-lg p-3 h-[64px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Total</p><p className="text-xl font-bold tabular-nums">{previewModal.total_members}</p></div>
                <div className="bg-[#F0F7F1] rounded-lg p-3 h-[64px]"><p className="text-[9px] uppercase tracking-wider text-[#4B6E4E]">Adds (021)</p><p className="text-xl font-bold tabular-nums text-[#4B6E4E]">{previewModal.adds}</p></div>
                <div className="bg-[#FFF5F5] rounded-lg p-3 h-[64px]"><p className="text-[9px] uppercase tracking-wider text-[#C24A3B]">Terms (024)</p><p className="text-xl font-bold tabular-nums text-[#C24A3B]">{previewModal.terms}</p></div>
                <div className="bg-[#F7F7F4] rounded-lg p-3 h-[64px]"><p className="text-[9px] uppercase tracking-wider text-[#8A8A85]">Format</p><p className="text-sm font-medium mt-1">{previewModal.format === 'hipaa_5010' ? 'HIPAA 5010 X12' : 'CSV'}</p></div>
              </div>
              {/* Raw content preview */}
              <div className="bg-[#1C1C1A] rounded-xl p-4 max-h-[300px] overflow-auto">
                <pre className="text-[11px] text-[#A8DB8F] font-['JetBrains_Mono'] whitespace-pre-wrap leading-relaxed" data-testid="preview-raw-content">
                  {previewModal.content?.substring(0, 3000)}
                  {previewModal.content?.length > 3000 && '\n\n... truncated ...'}
                </pre>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setPreviewModal(null)} data-testid="close-preview-btn">Close</Button>
                <Button className="btn-primary" onClick={() => {
                  downloadFile(previewModal.content, previewModal.filename);
                  toast.success('Downloaded');
                }} data-testid="download-from-preview-btn"><Download className="h-3.5 w-3.5 mr-1.5" />Download</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
