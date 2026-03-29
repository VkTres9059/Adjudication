import { useState, useEffect } from 'react';
import { priorAuthAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Shield,
  Plus,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Filter,
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

const STATUS_CONFIG = {
  pending: { label: 'Pending', icon: Clock, class: 'badge-pending' },
  approved: { label: 'Approved', icon: CheckCircle2, class: 'badge-approved' },
  denied: { label: 'Denied', icon: XCircle, class: 'badge-denied' },
  pended: { label: 'Pended', icon: Clock, class: 'badge-pended' },
};

export default function PriorAuth() {
  const [auths, setAuths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showDecide, setShowDecide] = useState(false);
  const [selectedAuth, setSelectedAuth] = useState(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    member_id: '',
    provider_npi: '',
    provider_name: '',
    service_type: 'medical',
    procedure_codes: '',
    diagnosis_codes: '',
    requested_date: new Date().toISOString().split('T')[0],
    clinical_notes: '',
    urgency: 'routine',
  });

  const [decisionForm, setDecisionForm] = useState({
    decision: 'approved',
    notes: '',
    approved_units: 1,
    valid_from: new Date().toISOString().split('T')[0],
    valid_to: '',
  });

  const fetchAuths = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;
      const response = await priorAuthAPI.list(params);
      setAuths(response.data);
    } catch (error) {
      toast.error('Failed to load prior authorizations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAuths(); }, [statusFilter]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await priorAuthAPI.create({
        ...form,
        procedure_codes: form.procedure_codes.split(',').map((c) => c.trim()).filter(Boolean),
        diagnosis_codes: form.diagnosis_codes.split(',').map((c) => c.trim()).filter(Boolean),
      });
      toast.success('Prior authorization request created');
      setShowCreate(false);
      setForm({ member_id: '', provider_npi: '', provider_name: '', service_type: 'medical', procedure_codes: '', diagnosis_codes: '', requested_date: new Date().toISOString().split('T')[0], clinical_notes: '', urgency: 'routine' });
      fetchAuths();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create request');
    } finally {
      setSaving(false);
    }
  };

  const handleDecide = async () => {
    if (!selectedAuth) return;
    setSaving(true);
    try {
      await priorAuthAPI.decide(selectedAuth.id, decisionForm);
      toast.success(`Prior auth ${decisionForm.decision}`);
      setShowDecide(false);
      fetchAuths();
    } catch (error) {
      toast.error('Failed to process decision');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="prior-auth-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Prior Authorization</h1>
          <p className="text-sm text-[#64645F] mt-1">Manage prior authorization requests and approvals</p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="new-prior-auth-btn">
          <Plus className="h-4 w-4 mr-2" />New Request
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <p className="metric-label">Pending</p>
          <p className="metric-value text-[#C9862B]">{auths.filter((a) => a.status === 'pending').length}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Approved</p>
          <p className="metric-value text-[#4B6E4E]">{auths.filter((a) => a.status === 'approved').length}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Denied</p>
          <p className="metric-value text-[#C24A3B]">{auths.filter((a) => a.status === 'denied').length}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Total</p>
          <p className="metric-value">{auths.length}</p>
        </div>
      </div>

      <div className="container-card">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48" data-testid="prior-auth-status-filter">
            <Filter className="h-4 w-4 mr-2 text-[#8A8A85]" /><SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="denied">Denied</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="container-card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
        ) : auths.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Shield className="h-12 w-12 text-[#E2E2DF] mb-4" />
            <p className="text-[#64645F]">No prior authorization requests</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>Auth #</TableHead>
                <TableHead>Member</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Codes</TableHead>
                <TableHead>Urgency</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-[80px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auths.map((auth) => {
                const cfg = STATUS_CONFIG[auth.status] || STATUS_CONFIG.pending;
                const Icon = cfg.icon;
                return (
                  <TableRow key={auth.id} className="table-row hover:bg-[#F7F7F4] transition-colors" data-testid={`prior-auth-row-${auth.id}`}>
                    <TableCell className="font-['JetBrains_Mono'] text-xs">{auth.auth_number}</TableCell>
                    <TableCell className="font-['JetBrains_Mono'] text-xs">{auth.member_id}</TableCell>
                    <TableCell className="max-w-[150px] truncate">{auth.provider_name}</TableCell>
                    <TableCell className="capitalize">{auth.service_type}</TableCell>
                    <TableCell className="font-['JetBrains_Mono'] text-xs">{auth.procedure_codes?.join(', ')}</TableCell>
                    <TableCell>
                      <Badge className={auth.urgency === 'urgent' ? 'badge-denied' : 'bg-[#F0F0EA] text-[#64645F]'}>{auth.urgency}</Badge>
                    </TableCell>
                    <TableCell><Badge className={`${cfg.class} flex items-center gap-1`}><Icon className="h-3 w-3" />{cfg.label}</Badge></TableCell>
                    <TableCell className="text-xs text-[#64645F]">{new Date(auth.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      {auth.status === 'pending' && (
                        <Button variant="ghost" size="sm" onClick={() => { setSelectedAuth(auth); setShowDecide(true); }} data-testid={`decide-${auth.id}`}>
                          <CheckCircle2 className="h-4 w-4 text-[#4B6E4E]" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Create Modal */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">New Prior Authorization Request</DialogTitle>
            <DialogDescription>Submit a request for service pre-approval</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid grid-cols-2 gap-4 py-4">
              <div className="space-y-2">
                <Label>Member ID</Label>
                <Input value={form.member_id} onChange={(e) => setForm({ ...form, member_id: e.target.value })} className="input-field" required data-testid="pa-member-id" />
              </div>
              <div className="space-y-2">
                <Label>Service Type</Label>
                <Select value={form.service_type} onValueChange={(v) => setForm({ ...form, service_type: v })}>
                  <SelectTrigger data-testid="pa-service-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="medical">Medical</SelectItem>
                    <SelectItem value="dental">Dental</SelectItem>
                    <SelectItem value="vision">Vision</SelectItem>
                    <SelectItem value="hearing">Hearing</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Provider NPI</Label>
                <Input value={form.provider_npi} onChange={(e) => setForm({ ...form, provider_npi: e.target.value })} className="input-field" required data-testid="pa-provider-npi" />
              </div>
              <div className="space-y-2">
                <Label>Provider Name</Label>
                <Input value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} className="input-field" required data-testid="pa-provider-name" />
              </div>
              <div className="space-y-2">
                <Label>Procedure Codes (comma-separated)</Label>
                <Input value={form.procedure_codes} onChange={(e) => setForm({ ...form, procedure_codes: e.target.value })} className="input-field font-['JetBrains_Mono'] text-xs" placeholder="99213, 99214" required data-testid="pa-procedure-codes" />
              </div>
              <div className="space-y-2">
                <Label>Diagnosis Codes (comma-separated)</Label>
                <Input value={form.diagnosis_codes} onChange={(e) => setForm({ ...form, diagnosis_codes: e.target.value })} className="input-field font-['JetBrains_Mono'] text-xs" placeholder="J06.9" required data-testid="pa-diagnosis-codes" />
              </div>
              <div className="space-y-2">
                <Label>Urgency</Label>
                <Select value={form.urgency} onValueChange={(v) => setForm({ ...form, urgency: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="routine">Routine</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                    <SelectItem value="emergent">Emergent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Requested Date</Label>
                <Input type="date" value={form.requested_date} onChange={(e) => setForm({ ...form, requested_date: e.target.value })} className="input-field" data-testid="pa-requested-date" />
              </div>
              <div className="space-y-2 col-span-2">
                <Label>Clinical Notes</Label>
                <Textarea value={form.clinical_notes} onChange={(e) => setForm({ ...form, clinical_notes: e.target.value })} className="input-field min-h-[80px]" placeholder="Clinical justification..." data-testid="pa-clinical-notes" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</Button>
              <Button type="submit" disabled={saving} className="btn-primary" data-testid="pa-submit-btn">
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Submit Request'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Decision Modal */}
      <Dialog open={showDecide} onOpenChange={setShowDecide}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Prior Auth Decision</DialogTitle>
            <DialogDescription>Review and decide on authorization request {selectedAuth?.auth_number}</DialogDescription>
          </DialogHeader>
          {selectedAuth && (
            <div className="space-y-4 py-4">
              <div className="bg-[#F7F7F4] rounded-lg p-4 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-[#64645F]">Member</span><span className="font-['JetBrains_Mono'] text-xs">{selectedAuth.member_id}</span></div>
                <div className="flex justify-between"><span className="text-[#64645F]">Provider</span><span>{selectedAuth.provider_name}</span></div>
                <div className="flex justify-between"><span className="text-[#64645F]">Codes</span><span className="font-['JetBrains_Mono'] text-xs">{selectedAuth.procedure_codes?.join(', ')}</span></div>
              </div>
              <div className="space-y-2">
                <Label>Decision</Label>
                <Select value={decisionForm.decision} onValueChange={(v) => setDecisionForm({ ...decisionForm, decision: v })}>
                  <SelectTrigger data-testid="pa-decision-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="approved">Approve</SelectItem>
                    <SelectItem value="denied">Deny</SelectItem>
                    <SelectItem value="pended">Pend for Review</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea value={decisionForm.notes} onChange={(e) => setDecisionForm({ ...decisionForm, notes: e.target.value })} className="input-field min-h-[80px]" data-testid="pa-decision-notes" />
              </div>
              {decisionForm.decision === 'approved' && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Valid From</Label>
                    <Input type="date" value={decisionForm.valid_from} onChange={(e) => setDecisionForm({ ...decisionForm, valid_from: e.target.value })} className="input-field" />
                  </div>
                  <div className="space-y-2">
                    <Label>Valid To</Label>
                    <Input type="date" value={decisionForm.valid_to} onChange={(e) => setDecisionForm({ ...decisionForm, valid_to: e.target.value })} className="input-field" />
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDecide(false)} className="btn-secondary">Cancel</Button>
            <Button onClick={handleDecide} disabled={saving} className={decisionForm.decision === 'approved' ? 'bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white' : decisionForm.decision === 'denied' ? 'btn-destructive' : 'btn-primary'} data-testid="pa-confirm-decision">
              {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : `${decisionForm.decision === 'approved' ? 'Approve' : decisionForm.decision === 'denied' ? 'Deny' : 'Pend'}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
