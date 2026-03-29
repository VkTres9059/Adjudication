import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { claimsAPI, membersAPI, plansAPI, examinerAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  ArrowLeft,
  FileText,
  User,
  Building2,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Stethoscope,
  Shield,
  ShieldOff,
  Lock,
  Unlock,
  Bell,
  Layers,
  Search,
  Zap,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';

const STATUS_CONFIG = {
  pending: { label: 'Pending', icon: Clock, class: 'badge-pending', color: '#C9862B' },
  in_review: { label: 'In Review', icon: Clock, class: 'badge-pended', color: '#4A6FA5' },
  approved: { label: 'Approved', icon: CheckCircle2, class: 'badge-approved', color: '#4B6E4E' },
  denied: { label: 'Denied', icon: XCircle, class: 'badge-denied', color: '#C24A3B' },
  duplicate: { label: 'Duplicate', icon: AlertTriangle, class: 'badge-duplicate', color: '#C24A3B' },
  pended: { label: 'Pended', icon: Clock, class: 'badge-pended', color: '#4A6FA5' },
  managerial_hold: { label: 'Managerial Hold', icon: Lock, class: 'bg-[#5C2D91] text-white border-0', color: '#5C2D91' },
  pending_review: { label: 'Pending Review', icon: Search, class: 'bg-[#C24A3B] text-white border-0', color: '#C24A3B' },
  pending_eligibility: { label: 'Pending Eligibility', icon: Clock, class: 'bg-[#C9862B] text-white border-0', color: '#C9862B' },
};

const HOLD_REASONS = [
  { value: 'medical_necessity', label: 'Medical Necessity Review' },
  { value: 'cob', label: 'Coordination of Benefits' },
  { value: 'subrogation', label: 'Subrogation' },
  { value: 'fraud_investigation', label: 'Fraud Investigation' },
  { value: 'stop_loss_review', label: 'Stop-Loss Review' },
];

export default function ClaimDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [member, setMember] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [showHoldModal, setShowHoldModal] = useState(false);
  const [showDeductibleModal, setShowDeductibleModal] = useState(false);
  const [actionType, setActionType] = useState('');
  const [actionNotes, setActionNotes] = useState('');
  const [denialReason, setDenialReason] = useState('');
  const [holdReason, setHoldReason] = useState('');
  const [holdNotes, setHoldNotes] = useState('');
  const [deductibleAmount, setDeductibleAmount] = useState('');

  useEffect(() => {
    fetchData();
  }, [id]);

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
      } catch { /* optional */ }
    } catch {
      toast.error('Failed to load claim');
      navigate('/claims');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async () => {
    setActionLoading(true);
    try {
      const payload = { action: actionType, notes: actionNotes };
      if (actionType === 'deny') payload.denial_reason = denialReason;
      await claimsAPI.adjudicate(id, payload);
      toast.success(`Claim ${actionType === 'approve' ? 'approved' : actionType === 'deny' ? 'denied' : 'updated'}`);
      const res = await claimsAPI.get(id);
      setClaim(res.data);
      setShowActionModal(false);
      setActionNotes('');
      setDenialReason('');
    } catch { toast.error('Failed to process claim'); }
    finally { setActionLoading(false); }
  };

  const handleHold = async () => {
    setActionLoading(true);
    try {
      const res = await examinerAPI.holdClaim(id, { reason_code: holdReason, notes: holdNotes });
      setClaim(res.data);
      toast.success('Claim placed on Managerial Hold');
      setShowHoldModal(false);
      setHoldReason('');
      setHoldNotes('');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to hold claim'); }
    finally { setActionLoading(false); }
  };

  const handleReleaseHold = async () => {
    setActionLoading(true);
    try {
      const res = await examinerAPI.releaseHold(id, 'Released by examiner');
      setClaim(res.data);
      toast.success('Hold released');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to release hold'); }
    finally { setActionLoading(false); }
  };

  const handleForcePreventive = async () => {
    setActionLoading(true);
    try {
      const res = await examinerAPI.forcePreventive(id, 'Examiner override: preventive');
      setClaim(res.data);
      toast.success('Claim overridden to Preventive — $0 member cost');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setActionLoading(false); }
  };

  const handleAdjustDeductible = async () => {
    setActionLoading(true);
    try {
      const res = await examinerAPI.adjustDeductible(id, parseFloat(deductibleAmount) || 0, 'Examiner deductible adjustment');
      setClaim(res.data);
      toast.success('Deductible adjusted');
      setShowDeductibleModal(false);
      setDeductibleAmount('');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setActionLoading(false); }
  };

  const handleCarrierNotification = async () => {
    setActionLoading(true);
    try {
      const res = await examinerAPI.carrierNotification(id, 'Specific attachment point notification');
      setClaim(res.data);
      toast.success('Carrier notification flagged');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setActionLoading(false); }
  };

  const openActionModal = (type) => { setActionType(type); setShowActionModal(true); };

  const formatCurrency = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>;
  if (!claim) return null;

  const StatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    return <Badge className={`${config.class} flex items-center gap-1.5`}><Icon className="h-3 w-3" />{config.label}</Badge>;
  };

  const canAdjudicate = ['pending', 'pended', 'in_review', 'pending_review'].includes(claim.status);
  const isDuplicate = claim.status === 'duplicate' || claim.duplicate_info;
  const isHeld = claim.status === 'managerial_hold';
  const isMecPlan = plan?.plan_template === 'mec_1';
  const hasStopLoss = plan && !isMecPlan && member?.group_id;

  return (
    <div className="space-y-6" data-testid="claim-detail-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/claims')} className="hover:bg-[#F0F0EA]" data-testid="back-btn">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Claim Details</h1>
              <StatusBadge status={claim.status} />
              {claim.tier_level && (
                <Badge className={
                  claim.tier_level === 1 ? 'bg-[#4B6E4E] text-white border-0 text-[10px]' :
                  claim.tier_level === 2 ? 'bg-[#C9862B] text-white border-0 text-[10px]' :
                  'bg-[#C24A3B] text-white border-0 text-[10px]'
                } data-testid="tier-badge">
                  {claim.tier_level === 1 && <><Zap className="h-2.5 w-2.5 mr-0.5" />Tier 1</>}
                  {claim.tier_level === 2 && <><Search className="h-2.5 w-2.5 mr-0.5" />Tier 2</>}
                  {claim.tier_level === 3 && <><Lock className="h-2.5 w-2.5 mr-0.5" />Tier 3</>}
                </Badge>
              )}
              {claim.audit_flag === 'post_payment_audit' && (
                <Badge className="bg-[#FFFBF5] text-[#C9862B] border border-[#C9862B] text-[10px]" data-testid="audit-flag-badge">Post-Payment Audit</Badge>
              )}
              {claim.carrier_notification && (
                <Badge className="bg-[#2563EB] text-white border-0 text-[10px]" data-testid="carrier-notification-badge"><Bell className="h-2.5 w-2.5 mr-0.5" />Carrier Notified</Badge>
              )}
              {claim.eligibility_source && claim.eligibility_source !== 'standard_hours' && (
                <Badge className={
                  claim.eligibility_source === 'bridge_payment' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                  claim.eligibility_source === 'reserve_draw' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                  claim.eligibility_source === 'insufficient' ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                  'bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]'
                } data-testid="eligibility-source-badge">
                  {claim.eligibility_source === 'bridge_payment' ? 'Bridge Payment' :
                   claim.eligibility_source === 'reserve_draw' ? 'Reserve Draw' :
                   claim.eligibility_source === 'insufficient' ? 'Hour Bank Insufficient' :
                   claim.eligibility_source?.replace(/_/g, ' ')}
                </Badge>
              )}
            </div>
            <p className="text-sm text-[#64645F] font-['JetBrains_Mono'] mt-1">{claim.claim_number}</p>
          </div>
        </div>

        <div className="flex gap-2 flex-wrap justify-end">
          {canAdjudicate && (
            <>
              <Button onClick={() => openActionModal('approve')} className="bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white" data-testid="approve-claim-btn"><CheckCircle2 className="h-4 w-4 mr-2" />Approve</Button>
              <Button onClick={() => openActionModal('deny')} className="btn-destructive" data-testid="deny-claim-btn"><XCircle className="h-4 w-4 mr-2" />Deny</Button>
              <Button onClick={() => openActionModal('pend')} variant="outline" className="btn-secondary" data-testid="pend-claim-btn"><Clock className="h-4 w-4 mr-2" />Pend</Button>
            </>
          )}
          {isDuplicate && claim.status !== 'approved' && (
            <Button onClick={() => openActionModal('override_duplicate')} variant="outline" className="btn-secondary" data-testid="override-duplicate-btn"><AlertTriangle className="h-4 w-4 mr-2" />Override</Button>
          )}
          {isHeld && (
            <Button onClick={handleReleaseHold} disabled={actionLoading} className="bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white" data-testid="release-hold-btn">
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Unlock className="h-4 w-4 mr-2" />}Release Hold
            </Button>
          )}
          {!isHeld && claim.status !== 'managerial_hold' && (
            <Button onClick={() => setShowHoldModal(true)} variant="outline" className="border-[#5C2D91] text-[#5C2D91] hover:bg-[#5C2D91]/5" data-testid="hold-claim-btn">
              <Lock className="h-4 w-4 mr-2" />Hold
            </Button>
          )}
        </div>
      </div>

      {/* Managerial Hold Banner */}
      {isHeld && claim.hold_info && (
        <div className="bg-[#F3EBF9] border border-[#5C2D91]/30 rounded-xl p-4" data-testid="hold-banner">
          <div className="flex items-start gap-3">
            <Lock className="h-5 w-5 text-[#5C2D91] mt-0.5" />
            <div>
              <p className="text-sm font-medium text-[#5C2D91]">Managerial Hold Active</p>
              <p className="text-xs text-[#64645F] mt-1">
                Reason: <span className="font-medium">{HOLD_REASONS.find(r => r.value === claim.hold_info.reason_code)?.label || claim.hold_info.reason_code}</span>
                {claim.hold_info.notes && <> &mdash; {claim.hold_info.notes}</>}
              </p>
              <p className="text-[10px] text-[#8A8A85] mt-1">Placed by {claim.hold_info.placed_by_name} at {new Date(claim.hold_info.placed_at).toLocaleString()}</p>
              <p className="text-[10px] text-[#C24A3B] mt-1 font-medium">This claim is excluded from Bordereaux and Financial reports until hold is released.</p>
            </div>
          </div>
        </div>
      )}

      {/* Duplicate Alert */}
      {claim.duplicate_info && (
        <div className="bg-[#FBEAE7] border border-[#C24A3B]/30 rounded-xl p-4" data-testid="duplicate-alert">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-[#C24A3B] mt-0.5" />
            <div>
              <p className="text-sm font-medium text-[#C24A3B]">Potential Duplicate Detected ({Math.round(claim.duplicate_info.match_score * 100)}% match)</p>
              <p className="text-sm text-[#64645F] mt-1">Matches claim <span className="font-['JetBrains_Mono']">{claim.duplicate_info.matched_claim_number}</span></p>
              <ul className="mt-2 space-y-1">
                {claim.duplicate_info.match_reasons?.map((reason, i) => (
                  <li key={i} className="text-xs text-[#64645F] flex items-center gap-2"><span className="w-1 h-1 bg-[#C24A3B] rounded-full" />{reason}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Plan Examiner Workspace */}
      {plan && (
        <div className="container-card" data-testid="examiner-workspace">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-[#64645F]" />
              <h3 className="text-sm font-medium text-[#1C1C1A]">Examiner Workspace</h3>
              {isMecPlan && <Badge className="bg-[#1A3636] text-white border-0 text-[10px]"><Shield className="h-2.5 w-2.5 mr-0.5" />MEC 1</Badge>}
              {!isMecPlan && <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]">Standard</Badge>}
            </div>
            <p className="text-[10px] text-[#8A8A85]">Plan: {plan.name}</p>
          </div>

          {isMecPlan ? (
            /* MEC 1: ACA Preventive Validator */
            <div className="bg-[#F7FAF7] rounded-lg p-4 border border-[#D4E5D6]" data-testid="mec-workspace">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-4 w-4 text-[#4B6E4E]" />
                <p className="text-sm font-medium text-[#4B6E4E]">ACA Preventive Validator</p>
              </div>
              <p className="text-xs text-[#64645F] mb-3">MEC 1 plans only cover ACA-compliant preventive services. Toggle the preventive flag to force $0 member cost on this claim.</p>
              <Button
                onClick={handleForcePreventive}
                disabled={actionLoading || claim.status === 'approved'}
                size="sm"
                className="bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white text-xs"
                data-testid="force-preventive-btn"
              >
                {actionLoading ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
                Force Preventive ($0 Member Cost)
              </Button>
            </div>
          ) : (
            /* Standard Plan: Deductible/OOP Tracker + Stop-Loss */
            <div className="space-y-3">
              <div className="bg-[#FFFBF5] rounded-lg p-4 border border-[#E8D5B5]" data-testid="standard-workspace">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="h-4 w-4 text-[#C9862B]" />
                  <p className="text-sm font-medium text-[#C9862B]">Deductible / OOP Tracker</p>
                </div>
                <p className="text-xs text-[#64645F] mb-3">Manually adjust the &ldquo;Applied to Deductible&rdquo; amount for this claim.</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#64645F]">Current member responsibility: <span className="font-['JetBrains_Mono'] font-semibold">{formatCurrency(claim.member_responsibility)}</span></span>
                  <Button
                    onClick={() => { setDeductibleAmount(String(claim.member_responsibility || 0)); setShowDeductibleModal(true); }}
                    disabled={actionLoading}
                    size="sm"
                    variant="outline"
                    className="border-[#C9862B] text-[#C9862B] hover:bg-[#C9862B]/5 text-xs"
                    data-testid="adjust-deductible-btn"
                  >
                    Adjust Deductible
                  </Button>
                </div>
              </div>
              {hasStopLoss && (
                <div className="bg-[#F5F7FF] rounded-lg p-4 border border-[#C0CFF5]" data-testid="stop-loss-workspace">
                  <div className="flex items-center gap-2 mb-2">
                    <Bell className="h-4 w-4 text-[#2563EB]" />
                    <p className="text-sm font-medium text-[#2563EB]">Specific Attachment Point</p>
                  </div>
                  <p className="text-xs text-[#64645F] mb-3">Flag this claim as a &ldquo;Specific Notification&rdquo; to the carrier when it approaches or exceeds the specific deductible.</p>
                  <Button
                    onClick={handleCarrierNotification}
                    disabled={actionLoading || claim.carrier_notification}
                    size="sm"
                    className={claim.carrier_notification ? 'bg-[#2563EB] text-white border-0 text-xs opacity-60' : 'bg-[#2563EB] hover:bg-[#1d4ed8] text-white text-xs'}
                    data-testid="carrier-notify-btn"
                  >
                    {actionLoading ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <Bell className="h-3 w-3 mr-1" />}
                    {claim.carrier_notification ? 'Notification Sent' : 'Flag Carrier Notification'}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="container-card">
          <div className="flex items-center gap-2 mb-4"><FileText className="h-4 w-4 text-[#64645F]" /><h3 className="text-sm font-medium text-[#1C1C1A]">Claim Information</h3></div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-[#64645F]">Type</dt><dd className="font-medium capitalize">{claim.claim_type}</dd></div>
            <div className="flex justify-between"><dt className="text-[#64645F]">Source</dt><dd className="font-medium capitalize">{claim.source || 'API'}</dd></div>
            <div className="flex justify-between"><dt className="text-[#64645F]">Created</dt><dd className="font-medium">{new Date(claim.created_at).toLocaleDateString()}</dd></div>
            {claim.adjudicated_at && <div className="flex justify-between"><dt className="text-[#64645F]">Adjudicated</dt><dd className="font-medium">{new Date(claim.adjudicated_at).toLocaleDateString()}</dd></div>}
          </dl>
        </div>
        <div className="container-card">
          <div className="flex items-center gap-2 mb-4"><User className="h-4 w-4 text-[#64645F]" /><h3 className="text-sm font-medium text-[#1C1C1A]">Member</h3></div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-[#64645F]">Member ID</dt><dd className="font-['JetBrains_Mono'] text-xs">{claim.member_id}</dd></div>
            {member && <>
              <div className="flex justify-between"><dt className="text-[#64645F]">Name</dt><dd className="font-medium">{member.first_name} {member.last_name}</dd></div>
              <div className="flex justify-between"><dt className="text-[#64645F]">DOB</dt><dd className="font-medium">{member.dob}</dd></div>
            </>}
            {plan && <div className="flex justify-between"><dt className="text-[#64645F]">Plan</dt><dd className="font-medium truncate max-w-[150px]">{plan.name}</dd></div>}
          </dl>
        </div>
        <div className="container-card">
          <div className="flex items-center gap-2 mb-4"><Building2 className="h-4 w-4 text-[#64645F]" /><h3 className="text-sm font-medium text-[#1C1C1A]">Provider</h3></div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-[#64645F]">Name</dt><dd className="font-medium truncate max-w-[150px]">{claim.provider_name}</dd></div>
            <div className="flex justify-between"><dt className="text-[#64645F]">NPI</dt><dd className="font-['JetBrains_Mono'] text-xs">{claim.provider_npi}</dd></div>
          </dl>
        </div>
      </div>

      {/* Financial Summary */}
      <div className="container-card">
        <div className="flex items-center gap-2 mb-4"><DollarSign className="h-4 w-4 text-[#64645F]" /><h3 className="text-sm font-medium text-[#1C1C1A]">Financial Summary</h3></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div><p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">Total Billed</p><p className="text-2xl font-semibold font-['Outfit'] text-[#1C1C1A]">{formatCurrency(claim.total_billed)}</p></div>
          <div><p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">Allowed</p><p className="text-2xl font-semibold font-['Outfit'] text-[#1C1C1A]">{formatCurrency(claim.total_allowed)}</p></div>
          <div><p className="text-xs uppercase tracking-[0.2em] text-[#4B6E4E] mb-1">Plan Paid</p><p className="text-2xl font-semibold font-['Outfit'] text-[#4B6E4E]">{formatCurrency(claim.total_paid)}</p></div>
          <div><p className="text-xs uppercase tracking-[0.2em] text-[#C9862B] mb-1">Member Responsibility</p><p className="text-2xl font-semibold font-['Outfit'] text-[#C9862B]">{formatCurrency(claim.member_responsibility)}</p></div>
        </div>
      </div>

      {/* Service Lines */}
      <div className="container-card p-0 overflow-hidden">
        <div className="p-6 border-b border-[#E2E2DF]"><div className="flex items-center gap-2"><Stethoscope className="h-4 w-4 text-[#64645F]" /><h3 className="text-sm font-medium text-[#1C1C1A]">Service Lines</h3></div></div>
        <Table>
          <TableHeader>
            <TableRow className="table-header">
              <TableHead>Line</TableHead><TableHead>CPT/HCPCS</TableHead><TableHead>Service Date</TableHead><TableHead>Units</TableHead>
              <TableHead className="text-right">Billed</TableHead><TableHead className="text-right">Allowed</TableHead>
              <TableHead className="text-right">Paid</TableHead><TableHead className="text-right">Member</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {claim.service_lines?.map((line, index) => (
              <TableRow key={index} className="table-row">
                <TableCell>{line.line_number}</TableCell>
                <TableCell className="font-['JetBrains_Mono'] text-xs">
                  <div className="flex items-center gap-2">
                    <span>{line.cpt_code}</span>
                    {line.modifier && <span className="text-[#8A8A85]">-{line.modifier}</span>}
                    {line.is_preventive && <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-[#4B6E4E]/10 text-[#4B6E4E] text-[10px] font-semibold uppercase tracking-wider">Preventive</span>}
                  </div>
                  {line.cpt_description && <p className="text-[10px] text-[#8A8A85] mt-0.5 font-sans max-w-[200px] truncate">{line.cpt_description}</p>}
                </TableCell>
                <TableCell>{line.service_date}</TableCell>
                <TableCell>{line.units}</TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs">{formatCurrency(line.billed_amount)}</TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs">{formatCurrency(line.allowed || 0)}</TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#4B6E4E]">{formatCurrency(line.paid || 0)}</TableCell>
                <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                  {line.is_preventive ? <span className="text-[#4B6E4E] font-semibold" data-testid={`eob-preventive-${line.line_number}`}>$0.00</span> : <span className="text-[#C9862B]">{formatCurrency(line.member_resp || 0)}</span>}
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
          {claim.diagnosis_codes?.map((code, index) => <Badge key={index} variant="outline" className="font-['JetBrains_Mono'] text-xs">{code}</Badge>)}
        </div>
      </div>

      {/* Adjudication Notes */}
      {claim.adjudication_notes?.length > 0 && (
        <div className="container-card">
          <h3 className="text-sm font-medium text-[#1C1C1A] mb-4">Adjudication Notes</h3>
          <div className="space-y-2">
            {claim.adjudication_notes.map((note, index) => (
              <div key={index} className={`p-3 rounded-lg text-sm ${
                note.includes('TIER 3') || note.includes('MANAGERIAL HOLD') ? 'bg-[#F3EBF9] text-[#5C2D91]' :
                note.includes('TIER 2') || note.includes('AUDIT') ? 'bg-[#FFFBF5] text-[#C9862B]' :
                note.includes('CARRIER') ? 'bg-[#F5F7FF] text-[#2563EB]' :
                note.includes('EXAMINER') ? 'bg-[#F7FAF7] text-[#4B6E4E]' :
                'bg-[#F7F7F4] text-[#64645F]'
              }`}>{note}</div>
            ))}
          </div>
        </div>
      )}

      {/* Standard Action Modal */}
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
                  <SelectTrigger data-testid="denial-reason-select"><SelectValue placeholder="Select a reason" /></SelectTrigger>
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
              <Textarea value={actionNotes} onChange={(e) => setActionNotes(e.target.value)} placeholder="Add any additional notes..." className="input-field min-h-[100px]" data-testid="action-notes-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowActionModal(false)} className="btn-secondary">Cancel</Button>
            <Button onClick={handleAction} disabled={actionLoading || (actionType === 'deny' && !denialReason)}
              className={actionType === 'approve' || actionType === 'override_duplicate' ? 'bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white' : actionType === 'deny' ? 'btn-destructive' : 'btn-primary'}
              data-testid="confirm-action-btn"
            >
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <>
                {actionType === 'approve' && 'Approve'}
                {actionType === 'deny' && 'Deny'}
                {actionType === 'pend' && 'Pend'}
                {actionType === 'override_duplicate' && 'Override & Approve'}
              </>}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hold Modal */}
      <Dialog open={showHoldModal} onOpenChange={setShowHoldModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Place Managerial Hold</DialogTitle>
            <DialogDescription>This claim will be frozen and excluded from all financial reports and Bordereaux until released by an admin.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Reason Code *</Label>
              <Select value={holdReason} onValueChange={setHoldReason}>
                <SelectTrigger data-testid="hold-reason-select"><SelectValue placeholder="Select reason..." /></SelectTrigger>
                <SelectContent>
                  {HOLD_REASONS.map(r => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <Textarea value={holdNotes} onChange={(e) => setHoldNotes(e.target.value)} placeholder="Additional context..." className="input-field min-h-[80px]" data-testid="hold-notes-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowHoldModal(false)} className="btn-secondary">Cancel</Button>
            <Button onClick={handleHold} disabled={actionLoading || !holdReason} className="bg-[#5C2D91] hover:bg-[#4a2475] text-white" data-testid="confirm-hold-btn">
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <><Lock className="h-4 w-4 mr-2" />Place Hold</>}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deductible Adjustment Modal */}
      <Dialog open={showDeductibleModal} onOpenChange={setShowDeductibleModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Adjust Deductible</DialogTitle>
            <DialogDescription>Manually adjust the member responsibility (Applied to Deductible) for this claim.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>New Member Responsibility ($)</Label>
              <Input type="number" step="0.01" value={deductibleAmount} onChange={(e) => setDeductibleAmount(e.target.value)} className="input-field" data-testid="deductible-amount-input" />
              <p className="text-[10px] text-[#8A8A85]">Current: {formatCurrency(claim.member_responsibility)}</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeductibleModal(false)} className="btn-secondary">Cancel</Button>
            <Button onClick={handleAdjustDeductible} disabled={actionLoading} className="bg-[#C9862B] hover:bg-[#b57725] text-white" data-testid="confirm-deductible-btn">
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Apply Adjustment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
