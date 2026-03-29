import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { examinerAPI } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import {
  ClipboardList,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Lock,
  Search,
  User,
  DollarSign,
  Clock,
  ArrowRight,
  UserCog,
  ChevronDown,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';

const STATUS_STYLES = {
  pending_review: { label: 'Pending Review', class: 'bg-[#C24A3B] text-white border-0', icon: Search },
  managerial_hold: { label: 'On Hold', class: 'bg-[#5C2D91] text-white border-0', icon: Lock },
};

export default function ExaminerQueue() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [queue, setQueue] = useState([]);
  const [examiners, setExaminers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [showReassign, setShowReassign] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [reassignClaimId, setReassignClaimId] = useState('');
  const [reassignExaminerId, setReassignExaminerId] = useState('');
  const [notesAction, setNotesAction] = useState('');
  const [notesClaimId, setNotesClaimId] = useState('');
  const [notesText, setNotesText] = useState('');
  const [sortBy, setSortBy] = useState('days');
  
  // Get user role from auth context
  const userRole = user?.role || '';

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const res = await examinerAPI.getQueue();
      setQueue(res.data);
    } catch { toast.error('Failed to load queue'); }
    finally { setLoading(false); }
  }, []);

  const fetchExaminers = useCallback(async () => {
    try {
      const res = await examinerAPI.listExaminers();
      setExaminers(res.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchQueue();
    fetchExaminers();
  }, [fetchQueue, fetchExaminers]);

  const handleQuickAction = async (claimId, action, notes = '') => {
    if (action === 'deny' || action === 'request_info') {
      setNotesAction(action);
      setNotesClaimId(claimId);
      setNotesText('');
      setShowNotes(true);
      return;
    }
    setActionLoading(claimId);
    try {
      await examinerAPI.quickAction(claimId, action, notes);
      toast.success(`Claim ${action === 'approve' ? 'approved' : action === 'deny' ? 'denied' : 'pended for info'}`);
      setQueue(prev => prev.filter(c => c.id !== claimId));
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setActionLoading(null); }
  };

  const handleNotesSubmit = async () => {
    setActionLoading(notesClaimId);
    setShowNotes(false);
    try {
      await examinerAPI.quickAction(notesClaimId, notesAction, notesText);
      toast.success(`Claim ${notesAction === 'deny' ? 'denied' : 'pended for info'}`);
      setQueue(prev => prev.filter(c => c.id !== notesClaimId));
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setActionLoading(null); setNotesText(''); }
  };

  const handleReassign = async () => {
    if (!reassignExaminerId) return;
    setActionLoading(reassignClaimId);
    setShowReassign(false);
    try {
      await examinerAPI.reassign(reassignClaimId, reassignExaminerId);
      toast.success('Claim reassigned');
      fetchQueue();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to reassign'); }
    finally { setActionLoading(null); }
  };

  const openReassign = (claimId) => {
    setReassignClaimId(claimId);
    setReassignExaminerId('');
    setShowReassign(true);
  };

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0);

  const sortedQueue = [...queue].sort((a, b) => {
    if (sortBy === 'days') return (b.days_in_queue || 0) - (a.days_in_queue || 0);
    if (sortBy === 'amount') return (b.total_billed || 0) - (a.total_billed || 0);
    return 0;
  });

  return (
    <div className="space-y-6" data-testid="examiner-queue-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">My Queue</h1>
          <p className="text-sm text-[#64645F] mt-1">Pending Review and On Hold claims assigned to you</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-[#64645F]">
            <span>Sort:</span>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[160px] h-8 text-xs" data-testid="sort-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="days">Days in Queue (Oldest)</SelectItem>
                <SelectItem value="amount">Dollar Amount (Highest)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={fetchQueue} variant="outline" className="btn-secondary" data-testid="refresh-queue-btn">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><ClipboardList className="h-4 w-4 text-[#64645F]" /><span className="metric-label">Total in Queue</span></div>
          <p className="metric-value" data-testid="queue-total">{queue.length}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><Search className="h-4 w-4 text-[#C24A3B]" /><span className="metric-label">Pending Review</span></div>
          <p className="metric-value text-[#C24A3B]" data-testid="queue-pending-review">{queue.filter(c => c.status === 'pending_review').length}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><Lock className="h-4 w-4 text-[#5C2D91]" /><span className="metric-label">On Hold</span></div>
          <p className="metric-value text-[#5C2D91]" data-testid="queue-on-hold">{queue.filter(c => c.status === 'managerial_hold').length}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2"><DollarSign className="h-4 w-4 text-[#64645F]" /><span className="metric-label">Total Exposure</span></div>
          <p className="metric-value" data-testid="queue-exposure">{fmt(queue.reduce((s, c) => s + (c.total_billed || 0), 0))}</p>
        </div>
      </div>

      {/* Queue Table */}
      <div className="container-card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48"><RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" /></div>
        ) : sortedQueue.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48">
            <ClipboardList className="h-10 w-10 text-[#E2E2DF] mb-3" />
            <p className="text-[#64645F] font-medium">Queue is clear</p>
            <p className="text-sm text-[#8A8A85]">No claims require your review</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>Claim #</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Member</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Billed</TableHead>
                <TableHead className="text-right">Days</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Assigned To</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedQueue.map((claim) => {
                const st = STATUS_STYLES[claim.status] || STATUS_STYLES.pending_review;
                const StIcon = st.icon;
                const isProcessing = actionLoading === claim.id;
                return (
                  <TableRow key={claim.id} className="table-row" data-testid={`queue-row-${claim.id}`}>
                    <TableCell>
                      <button
                        className="font-['JetBrains_Mono'] text-xs text-[#1A3636] hover:underline cursor-pointer"
                        onClick={() => navigate(`/claims/${claim.id}`)}
                        data-testid={`queue-claim-link-${claim.id}`}
                      >
                        {claim.claim_number}
                      </button>
                    </TableCell>
                    <TableCell>
                      <Badge className={`${st.class} text-[10px] flex items-center gap-1 w-fit`}>
                        <StIcon className="h-2.5 w-2.5" />{st.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-['JetBrains_Mono'] text-xs">{claim.member_id}</TableCell>
                    <TableCell className="capitalize text-xs">{claim.claim_type}</TableCell>
                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold">{fmt(claim.total_billed)}</TableCell>
                    <TableCell className="text-right">
                      <Badge className={
                        claim.days_in_queue > 5 ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                        claim.days_in_queue > 2 ? 'bg-[#C9862B] text-white border-0 text-[10px]' :
                        'bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]'
                      }>
                        {claim.days_in_queue}d
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {claim.tier_level && (
                        <Badge className={
                          claim.tier_level === 3 ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                          'bg-[#C9862B] text-white border-0 text-[10px]'
                        }>T{claim.tier_level}</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate max-w-[100px]">{claim.assigned_to_name || 'Unassigned'}</span>
                        {userRole === 'admin' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); openReassign(claim.id); }}
                            className="text-[#8A8A85] hover:text-[#1A3636] transition-colors"
                            title="Reassign"
                            data-testid={`reassign-btn-${claim.id}`}
                          >
                            <UserCog className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); handleQuickAction(claim.id, 'approve'); }}
                          disabled={isProcessing}
                          className="h-7 px-2.5 bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white text-[10px]"
                          data-testid={`quick-approve-${claim.id}`}
                        >
                          {isProcessing ? <RefreshCw className="h-3 w-3 animate-spin" /> : <><CheckCircle2 className="h-3 w-3 mr-0.5" />Approve</>}
                        </Button>
                        <Button
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); handleQuickAction(claim.id, 'deny'); }}
                          disabled={isProcessing}
                          className="h-7 px-2.5 bg-[#C24A3B] hover:bg-[#a93e31] text-white text-[10px]"
                          data-testid={`quick-deny-${claim.id}`}
                        >
                          <XCircle className="h-3 w-3 mr-0.5" />Deny
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => { e.stopPropagation(); handleQuickAction(claim.id, 'request_info'); }}
                          disabled={isProcessing}
                          className="h-7 px-2.5 border-[#C9862B] text-[#C9862B] hover:bg-[#C9862B]/5 text-[10px]"
                          data-testid={`quick-info-${claim.id}`}
                        >
                          <HelpCircle className="h-3 w-3 mr-0.5" />Info
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Reassign Modal */}
      <Dialog open={showReassign} onOpenChange={setShowReassign}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Reassign Claim</DialogTitle>
            <DialogDescription>Select an examiner to reassign this claim to.</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-3">
            <Select value={reassignExaminerId} onValueChange={setReassignExaminerId}>
              <SelectTrigger data-testid="reassign-examiner-select"><SelectValue placeholder="Select examiner..." /></SelectTrigger>
              <SelectContent>
                {examiners.map(ex => (
                  <SelectItem key={ex.id} value={ex.id}>
                    {ex.name || ex.email} ({ex.role === 'admin' ? 'Senior' : 'Junior'})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReassign(false)} className="btn-secondary">Cancel</Button>
            <Button onClick={handleReassign} disabled={!reassignExaminerId} className="btn-primary" data-testid="confirm-reassign-btn">Reassign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Notes Modal (for Deny / Request Info) */}
      <Dialog open={showNotes} onOpenChange={setShowNotes}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">
              {notesAction === 'deny' ? 'Deny Claim' : 'Request Information'}
            </DialogTitle>
            <DialogDescription>
              {notesAction === 'deny' ? 'Provide a reason for denying this claim.' : 'Describe what additional information is needed.'}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              value={notesText}
              onChange={(e) => setNotesText(e.target.value)}
              placeholder={notesAction === 'deny' ? 'Denial reason...' : 'Information needed...'}
              className="input-field min-h-[100px]"
              data-testid="quick-action-notes"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNotes(false)} className="btn-secondary">Cancel</Button>
            <Button
              onClick={handleNotesSubmit}
              className={notesAction === 'deny' ? 'bg-[#C24A3B] hover:bg-[#a93e31] text-white' : 'bg-[#C9862B] hover:bg-[#b57725] text-white'}
              data-testid="confirm-quick-action-btn"
            >
              {notesAction === 'deny' ? 'Deny' : 'Request Info'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
