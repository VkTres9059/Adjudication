import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { claimsAPI, membersAPI, plansAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  ArrowLeft,
  FileText,
  User,
  Building2,
  Calendar,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Stethoscope,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const STATUS_CONFIG = {
  pending: { label: 'Pending', icon: Clock, class: 'badge-pending', color: '#C9862B' },
  in_review: { label: 'In Review', icon: Clock, class: 'badge-pended', color: '#4A6FA5' },
  approved: { label: 'Approved', icon: CheckCircle2, class: 'badge-approved', color: '#4B6E4E' },
  denied: { label: 'Denied', icon: XCircle, class: 'badge-denied', color: '#C24A3B' },
  duplicate: { label: 'Duplicate', icon: AlertTriangle, class: 'badge-duplicate', color: '#C24A3B' },
  pended: { label: 'Pended', icon: Clock, class: 'badge-pended', color: '#4A6FA5' },
};

export default function ClaimDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [member, setMember] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [actionType, setActionType] = useState('');
  const [actionNotes, setActionNotes] = useState('');
  const [denialReason, setDenialReason] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const claimRes = await claimsAPI.get(id);
        setClaim(claimRes.data);

        try {
          const memberRes = await membersAPI.get(claimRes.data.member_id);
          setMember(memberRes.data);

          if (memberRes.data.plan_id) {
            const planRes = await plansAPI.get(memberRes.data.plan_id);
            setPlan(planRes.data);
          }
        } catch {
          // Member/plan lookup optional
        }
      } catch (error) {
        console.error('Failed to fetch claim:', error);
        toast.error('Failed to load claim');
        navigate('/claims');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, navigate]);

  const handleAction = async () => {
    setActionLoading(true);
    try {
      const payload = {
        action: actionType,
        notes: actionNotes,
      };
      if (actionType === 'deny') {
        payload.denial_reason = denialReason;
      }

      await claimsAPI.adjudicate(id, payload);
      toast.success(`Claim ${actionType === 'approve' ? 'approved' : actionType === 'deny' ? 'denied' : 'updated'} successfully`);
      
      // Refresh claim data
      const claimRes = await claimsAPI.get(id);
      setClaim(claimRes.data);
      setShowActionModal(false);
      setActionNotes('');
      setDenialReason('');
    } catch (error) {
      toast.error('Failed to process claim');
    } finally {
      setActionLoading(false);
    }
  };

  const openActionModal = (type) => {
    setActionType(type);
    setShowActionModal(true);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value || 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
      </div>
    );
  }

  if (!claim) return null;

  const StatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    return (
      <Badge className={`${config.class} flex items-center gap-1.5`}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const canAdjudicate = ['pending', 'pended', 'in_review'].includes(claim.status);
  const isDuplicate = claim.status === 'duplicate' || claim.duplicate_info;

  return (
    <div className="space-y-6" data-testid="claim-detail-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/claims')}
            className="hover:bg-[#F0F0EA]"
            data-testid="back-btn"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
                Claim Details
              </h1>
              <StatusBadge status={claim.status} />
            </div>
            <p className="text-sm text-[#64645F] font-['JetBrains_Mono'] mt-1">
              {claim.claim_number}
            </p>
          </div>
        </div>
        
        {canAdjudicate && (
          <div className="flex gap-3">
            <Button
              onClick={() => openActionModal('approve')}
              className="bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white"
              data-testid="approve-claim-btn"
            >
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Approve
            </Button>
            <Button
              onClick={() => openActionModal('deny')}
              className="btn-destructive"
              data-testid="deny-claim-btn"
            >
              <XCircle className="h-4 w-4 mr-2" />
              Deny
            </Button>
            <Button
              onClick={() => openActionModal('pend')}
              variant="outline"
              className="btn-secondary"
              data-testid="pend-claim-btn"
            >
              <Clock className="h-4 w-4 mr-2" />
              Pend
            </Button>
          </div>
        )}

        {isDuplicate && claim.status !== 'approved' && (
          <Button
            onClick={() => openActionModal('override_duplicate')}
            variant="outline"
            className="btn-secondary"
            data-testid="override-duplicate-btn"
          >
            <AlertTriangle className="h-4 w-4 mr-2" />
            Override & Approve
          </Button>
        )}
      </div>

      {/* Duplicate Alert */}
      {claim.duplicate_info && (
        <div 
          className="bg-[#FBEAE7] border border-[#C24A3B]/30 rounded-xl p-4"
          data-testid="duplicate-alert"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-[#C24A3B] mt-0.5" />
            <div>
              <p className="text-sm font-medium text-[#C24A3B]">
                Potential Duplicate Detected ({Math.round(claim.duplicate_info.match_score * 100)}% match)
              </p>
              <p className="text-sm text-[#64645F] mt-1">
                Matches claim{' '}
                <span className="font-['JetBrains_Mono']">
                  {claim.duplicate_info.matched_claim_number}
                </span>
              </p>
              <ul className="mt-2 space-y-1">
                {claim.duplicate_info.match_reasons?.map((reason, i) => (
                  <li key={i} className="text-xs text-[#64645F] flex items-center gap-2">
                    <span className="w-1 h-1 bg-[#C24A3B] rounded-full" />
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Claim Info */}
        <div className="container-card">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-4 w-4 text-[#64645F]" />
            <h3 className="text-sm font-medium text-[#1C1C1A]">Claim Information</h3>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-[#64645F]">Type</dt>
              <dd className="font-medium capitalize">{claim.claim_type}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#64645F]">Source</dt>
              <dd className="font-medium capitalize">{claim.source || 'API'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#64645F]">Created</dt>
              <dd className="font-medium">{new Date(claim.created_at).toLocaleDateString()}</dd>
            </div>
            {claim.adjudicated_at && (
              <div className="flex justify-between">
                <dt className="text-[#64645F]">Adjudicated</dt>
                <dd className="font-medium">{new Date(claim.adjudicated_at).toLocaleDateString()}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Member Info */}
        <div className="container-card">
          <div className="flex items-center gap-2 mb-4">
            <User className="h-4 w-4 text-[#64645F]" />
            <h3 className="text-sm font-medium text-[#1C1C1A]">Member</h3>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-[#64645F]">Member ID</dt>
              <dd className="font-['JetBrains_Mono'] text-xs">{claim.member_id}</dd>
            </div>
            {member && (
              <>
                <div className="flex justify-between">
                  <dt className="text-[#64645F]">Name</dt>
                  <dd className="font-medium">{member.first_name} {member.last_name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-[#64645F]">DOB</dt>
                  <dd className="font-medium">{member.dob}</dd>
                </div>
              </>
            )}
            {plan && (
              <div className="flex justify-between">
                <dt className="text-[#64645F]">Plan</dt>
                <dd className="font-medium truncate max-w-[150px]">{plan.name}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Provider Info */}
        <div className="container-card">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="h-4 w-4 text-[#64645F]" />
            <h3 className="text-sm font-medium text-[#1C1C1A]">Provider</h3>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-[#64645F]">Name</dt>
              <dd className="font-medium truncate max-w-[150px]">{claim.provider_name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#64645F]">NPI</dt>
              <dd className="font-['JetBrains_Mono'] text-xs">{claim.provider_npi}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Financial Summary */}
      <div className="container-card">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="h-4 w-4 text-[#64645F]" />
          <h3 className="text-sm font-medium text-[#1C1C1A]">Financial Summary</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">Total Billed</p>
            <p className="text-2xl font-semibold font-['Outfit'] text-[#1C1C1A]">
              {formatCurrency(claim.total_billed)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">Allowed</p>
            <p className="text-2xl font-semibold font-['Outfit'] text-[#1C1C1A]">
              {formatCurrency(claim.total_allowed)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#4B6E4E] mb-1">Plan Paid</p>
            <p className="text-2xl font-semibold font-['Outfit'] text-[#4B6E4E]">
              {formatCurrency(claim.total_paid)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#C9862B] mb-1">Member Responsibility</p>
            <p className="text-2xl font-semibold font-['Outfit'] text-[#C9862B]">
              {formatCurrency(claim.member_responsibility)}
            </p>
          </div>
        </div>
      </div>

      {/* Service Lines */}
      <div className="container-card p-0 overflow-hidden">
        <div className="p-6 border-b border-[#E2E2DF]">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-[#64645F]" />
            <h3 className="text-sm font-medium text-[#1C1C1A]">Service Lines</h3>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="table-header">
              <TableHead>Line</TableHead>
              <TableHead>CPT/HCPCS</TableHead>
              <TableHead>Service Date</TableHead>
              <TableHead>Units</TableHead>
              <TableHead className="text-right">Billed</TableHead>
              <TableHead className="text-right">Allowed</TableHead>
              <TableHead className="text-right">Paid</TableHead>
              <TableHead className="text-right">Member</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {claim.service_lines?.map((line, index) => (
              <TableRow key={index} className="table-row">
                <TableCell>{line.line_number}</TableCell>
                <TableCell className="font-['JetBrains_Mono'] text-xs">
                  {line.cpt_code}
                  {line.modifier && <span className="text-[#8A8A85]">-{line.modifier}</span>}
                </TableCell>
                <TableCell>{line.service_date}</TableCell>
                <TableCell>{line.units}</TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                  {formatCurrency(line.billed_amount)}
                </TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                  {formatCurrency(line.allowed || 0)}
                </TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#4B6E4E]">
                  {formatCurrency(line.paid || 0)}
                </TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#C9862B]">
                  {formatCurrency(line.member_resp || 0)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Diagnosis Codes */}
      <div className="container-card">
        <h3 className="text-sm font-medium text-[#1C1C1A] mb-4">Diagnosis Codes</h3>
        <div className="flex flex-wrap gap-2">
          {claim.diagnosis_codes?.map((code, index) => (
            <Badge 
              key={index}
              variant="outline"
              className="font-['JetBrains_Mono'] text-xs"
            >
              {code}
            </Badge>
          ))}
        </div>
      </div>

      {/* Adjudication Notes */}
      {claim.adjudication_notes?.length > 0 && (
        <div className="container-card">
          <h3 className="text-sm font-medium text-[#1C1C1A] mb-4">Adjudication Notes</h3>
          <div className="space-y-2">
            {claim.adjudication_notes.map((note, index) => (
              <div 
                key={index}
                className="p-3 bg-[#F7F7F4] rounded-lg text-sm text-[#64645F]"
              >
                {note}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Modal */}
      <Dialog open={showActionModal} onOpenChange={setShowActionModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">
              {actionType === 'approve' && 'Approve Claim'}
              {actionType === 'deny' && 'Deny Claim'}
              {actionType === 'pend' && 'Pend Claim'}
              {actionType === 'override_duplicate' && 'Override Duplicate & Approve'}
            </DialogTitle>
            <DialogDescription>
              {actionType === 'approve' && 'This will approve the claim and process payment.'}
              {actionType === 'deny' && 'Please provide a reason for denying this claim.'}
              {actionType === 'pend' && 'This will place the claim on hold for further review.'}
              {actionType === 'override_duplicate' && 'This will override the duplicate flag and approve the claim.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {actionType === 'deny' && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-[#1C1C1A]">Denial Reason</label>
                <Select value={denialReason} onValueChange={setDenialReason}>
                  <SelectTrigger data-testid="denial-reason-select">
                    <SelectValue placeholder="Select a reason" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="not_covered">Service not covered</SelectItem>
                    <SelectItem value="no_auth">Missing prior authorization</SelectItem>
                    <SelectItem value="ineligible">Member ineligible</SelectItem>
                    <SelectItem value="duplicate">Duplicate claim</SelectItem>
                    <SelectItem value="coding_error">Coding error</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium text-[#1C1C1A]">Notes (Optional)</label>
              <Textarea
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                placeholder="Add any additional notes..."
                className="input-field min-h-[100px]"
                data-testid="action-notes-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowActionModal(false)}
              className="btn-secondary"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAction}
              disabled={actionLoading || (actionType === 'deny' && !denialReason)}
              className={
                actionType === 'approve' || actionType === 'override_duplicate'
                  ? 'bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white'
                  : actionType === 'deny'
                  ? 'btn-destructive'
                  : 'btn-primary'
              }
              data-testid="confirm-action-btn"
            >
              {actionLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  {actionType === 'approve' && 'Approve'}
                  {actionType === 'deny' && 'Deny'}
                  {actionType === 'pend' && 'Pend'}
                  {actionType === 'override_duplicate' && 'Override & Approve'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
