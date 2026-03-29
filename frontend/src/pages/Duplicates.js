import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { duplicatesAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Eye,
  Filter,
} from 'lucide-react';
import { Button } from '../components/ui/button';
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

const TYPE_CONFIG = {
  exact: { label: 'Exact', class: 'bg-[#FBEAE7] text-[#C24A3B] border border-[#C24A3B]' },
  near: { label: 'Near', class: 'bg-[#FDF3E1] text-[#C9862B]' },
  line_level: { label: 'Line Level', class: 'bg-[#EEF3F9] text-[#4A6FA5]' },
};

const STATUS_CONFIG = {
  pending: { label: 'Pending Review', class: 'badge-pending' },
  confirm_duplicate: { label: 'Confirmed', class: 'badge-denied' },
  not_duplicate: { label: 'Cleared', class: 'badge-approved' },
  overridden: { label: 'Overridden', class: 'badge-pended' },
};

export default function Duplicates() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [resolving, setResolving] = useState(false);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;
      if (typeFilter && typeFilter !== 'all') params.duplicate_type = typeFilter;
      
      const response = await duplicatesAPI.list(params);
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch duplicate alerts:', error);
      toast.error('Failed to load duplicate alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter, typeFilter]);

  const handleResolve = async (resolution) => {
    if (!selectedAlert) return;
    
    setResolving(true);
    try {
      await duplicatesAPI.resolve(selectedAlert.id, resolution);
      toast.success(
        resolution === 'confirm_duplicate'
          ? 'Marked as duplicate'
          : 'Cleared as not a duplicate'
      );
      setShowResolveModal(false);
      setSelectedAlert(null);
      fetchAlerts();
    } catch (error) {
      toast.error('Failed to resolve alert');
    } finally {
      setResolving(false);
    }
  };

  const openResolveModal = (alert) => {
    setSelectedAlert(alert);
    setShowResolveModal(true);
  };

  return (
    <div className="space-y-6" data-testid="duplicates-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Duplicate Alerts
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            Review and resolve potential duplicate claims
          </p>
        </div>
        <Button
          onClick={fetchAlerts}
          variant="outline"
          className="btn-secondary"
          data-testid="refresh-duplicates-btn"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <p className="metric-label">Pending Review</p>
          <p className="metric-value text-[#C9862B]">
            {alerts.filter((a) => a.status === 'pending').length}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Exact Matches</p>
          <p className="metric-value text-[#C24A3B]">
            {alerts.filter((a) => a.duplicate_type === 'exact').length}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Near Matches</p>
          <p className="metric-value text-[#C9862B]">
            {alerts.filter((a) => a.duplicate_type === 'near').length}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Resolved Today</p>
          <p className="metric-value text-[#4B6E4E]">
            {alerts.filter((a) => a.status !== 'pending').length}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="container-card">
        <div className="flex gap-4">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-48" data-testid="status-filter">
              <Filter className="h-4 w-4 mr-2 text-[#8A8A85]" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending Review</SelectItem>
              <SelectItem value="confirm_duplicate">Confirmed</SelectItem>
              <SelectItem value="not_duplicate">Cleared</SelectItem>
              <SelectItem value="overridden">Overridden</SelectItem>
            </SelectContent>
          </Select>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-40" data-testid="type-filter">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="exact">Exact Match</SelectItem>
              <SelectItem value="near">Near Match</SelectItem>
              <SelectItem value="line_level">Line Level</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="container-card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <CheckCircle2 className="h-12 w-12 text-[#4B6E4E] mb-4" />
            <p className="text-[#64645F] mb-2">No duplicate alerts</p>
            <p className="text-sm text-[#8A8A85]">
              All potential duplicates have been reviewed
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>New Claim</TableHead>
                <TableHead>Matched Claim</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Reasons</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((alert) => (
                <TableRow
                  key={alert.id}
                  className={`table-row hover:bg-[#F7F7F4] transition-colors ${
                    alert.status === 'pending' && alert.duplicate_type === 'exact'
                      ? 'bg-[#FBEAE7]/30'
                      : ''
                  }`}
                  data-testid={`duplicate-row-${alert.id}`}
                >
                  <TableCell>
                    <Link
                      to={`/claims/${alert.claim_id}`}
                      className="font-['JetBrains_Mono'] text-xs text-[#1A3636] hover:underline"
                    >
                      {alert.claim_number}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Link
                      to={`/claims/${alert.matched_claim_id}`}
                      className="font-['JetBrains_Mono'] text-xs text-[#1A3636] hover:underline"
                    >
                      {alert.matched_claim_number}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge className={TYPE_CONFIG[alert.duplicate_type]?.class || ''}>
                      {TYPE_CONFIG[alert.duplicate_type]?.label || alert.duplicate_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-[#E2E2DF] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            alert.match_score >= 0.9
                              ? 'bg-[#C24A3B]'
                              : alert.match_score >= 0.7
                              ? 'bg-[#C9862B]'
                              : 'bg-[#4A6FA5]'
                          }`}
                          style={{ width: `${alert.match_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-['JetBrains_Mono']">
                        {Math.round(alert.match_score * 100)}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <ul className="text-xs text-[#64645F] space-y-0.5">
                      {alert.match_reasons?.slice(0, 2).map((reason, i) => (
                        <li key={i} className="truncate">• {reason}</li>
                      ))}
                      {alert.match_reasons?.length > 2 && (
                        <li className="text-[#8A8A85]">
                          +{alert.match_reasons.length - 2} more
                        </li>
                      )}
                    </ul>
                  </TableCell>
                  <TableCell>
                    <Badge className={STATUS_CONFIG[alert.status]?.class || ''}>
                      {STATUS_CONFIG[alert.status]?.label || alert.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-[#64645F]">
                    {new Date(alert.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Link to={`/claims/${alert.claim_id}`}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:bg-[#F0F0EA]"
                          data-testid={`view-claim-${alert.id}`}
                        >
                          <Eye className="h-4 w-4 text-[#64645F]" />
                        </Button>
                      </Link>
                      {alert.status === 'pending' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:bg-[#EDF2EE]"
                          onClick={() => openResolveModal(alert)}
                          data-testid={`resolve-${alert.id}`}
                        >
                          <CheckCircle2 className="h-4 w-4 text-[#4B6E4E]" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Summary */}
      <div className="text-sm text-[#64645F]">
        Showing {alerts.length} duplicate alerts
      </div>

      {/* Resolve Modal */}
      <Dialog open={showResolveModal} onOpenChange={setShowResolveModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Resolve Duplicate Alert</DialogTitle>
            <DialogDescription>
              Review the match details and choose how to resolve this alert
            </DialogDescription>
          </DialogHeader>

          {selectedAlert && (
            <div className="py-4 space-y-4">
              <div className="bg-[#F7F7F4] rounded-lg p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-[#64645F]">New Claim</span>
                  <span className="font-['JetBrains_Mono'] text-xs">
                    {selectedAlert.claim_number}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[#64645F]">Matched Claim</span>
                  <span className="font-['JetBrains_Mono'] text-xs">
                    {selectedAlert.matched_claim_number}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[#64645F]">Match Score</span>
                  <span className="font-medium">
                    {Math.round(selectedAlert.match_score * 100)}%
                  </span>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-[#1C1C1A] mb-2">Match Reasons</p>
                <ul className="text-sm text-[#64645F] space-y-1">
                  {selectedAlert.match_reasons?.map((reason, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-[#C24A3B] mt-0.5 flex-shrink-0" />
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <DialogFooter className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setShowResolveModal(false)}
              className="btn-secondary flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={() => handleResolve('not_duplicate')}
              disabled={resolving}
              className="bg-[#4B6E4E] hover:bg-[#3d5a3f] text-white flex-1"
              data-testid="clear-duplicate-btn"
            >
              {resolving ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Not a Duplicate
                </>
              )}
            </Button>
            <Button
              onClick={() => handleResolve('confirm_duplicate')}
              disabled={resolving}
              className="btn-destructive flex-1"
              data-testid="confirm-duplicate-btn"
            >
              {resolving ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <XCircle className="h-4 w-4 mr-2" />
                  Confirm Duplicate
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
