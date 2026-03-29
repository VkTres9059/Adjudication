import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { claimsAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Search,
  Filter,
  Plus,
  FileText,
  ChevronRight,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Lock,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
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
import { Badge } from '../components/ui/badge';
import NewClaimModal from '../components/NewClaimModal';

const STATUS_CONFIG = {
  pending: { label: 'Pending', icon: Clock, class: 'badge-pending' },
  in_review: { label: 'In Review', icon: Clock, class: 'badge-pended' },
  approved: { label: 'Approved', icon: CheckCircle2, class: 'badge-approved' },
  denied: { label: 'Denied', icon: XCircle, class: 'badge-denied' },
  duplicate: { label: 'Duplicate', icon: AlertTriangle, class: 'badge-duplicate' },
  pended: { label: 'Pended', icon: Clock, class: 'badge-pended' },
  managerial_hold: { label: 'On Hold', icon: Lock, class: 'bg-[#5C2D91] text-white border-0' },
  pending_review: { label: 'Pending Review', icon: Lock, class: 'bg-[#C24A3B] text-white border-0' },
  pending_eligibility: { label: 'Pending Elig.', icon: Clock, class: 'bg-[#C9862B] text-white border-0' },
};

export default function Claims() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewClaim, setShowNewClaim] = useState(false);
  const [filters, setFilters] = useState({
    status: searchParams.get('status') || '',
    claim_type: searchParams.get('claim_type') || '',
    search: searchParams.get('search') || '',
  });

  const fetchClaims = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.claim_type) params.claim_type = filters.claim_type;
      
      const response = await claimsAPI.list(params);
      setClaims(response.data);
    } catch (error) {
      console.error('Failed to fetch claims:', error);
      toast.error('Failed to load claims');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, [filters.status, filters.claim_type]);

  const handleFilterChange = (key, value) => {
    const actualValue = value === 'all' ? '' : value;
    setFilters((prev) => ({ ...prev, [key]: actualValue }));
    if (actualValue) {
      searchParams.set(key, actualValue);
    } else {
      searchParams.delete(key);
    }
    setSearchParams(searchParams);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value || 0);
  };

  const filteredClaims = claims.filter((claim) => {
    if (!filters.search) return true;
    const search = filters.search.toLowerCase();
    return (
      claim.claim_number.toLowerCase().includes(search) ||
      claim.member_id.toLowerCase().includes(search) ||
      claim.provider_name.toLowerCase().includes(search)
    );
  });

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

  return (
    <div className="space-y-6" data-testid="claims-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Claims
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            Manage and adjudicate claims
          </p>
        </div>
        <Button
          onClick={() => setShowNewClaim(true)}
          className="btn-primary"
          data-testid="new-claim-btn"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Claim
        </Button>
      </div>

      {/* Filters */}
      <div className="container-card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
            <Input
              placeholder="Search by claim #, member ID, or provider..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="pl-10 input-field"
              data-testid="claims-search-input"
            />
          </div>
          <div className="flex gap-3">
            <Select
              value={filters.status}
              onValueChange={(value) => handleFilterChange('status', value)}
            >
              <SelectTrigger className="w-40" data-testid="status-filter">
                <Filter className="h-4 w-4 mr-2 text-[#8A8A85]" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="pended">Pended</SelectItem>
                <SelectItem value="pending_review">Pending Review</SelectItem>
                <SelectItem value="pending_eligibility">Pending Eligibility</SelectItem>
                <SelectItem value="managerial_hold">On Hold</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="denied">Denied</SelectItem>
                <SelectItem value="duplicate">Duplicate</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={filters.claim_type}
              onValueChange={(value) => handleFilterChange('claim_type', value)}
            >
              <SelectTrigger className="w-40" data-testid="type-filter">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="medical">Medical</SelectItem>
                <SelectItem value="dental">Dental</SelectItem>
                <SelectItem value="vision">Vision</SelectItem>
                <SelectItem value="hearing">Hearing</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              onClick={fetchClaims}
              className="btn-secondary"
              data-testid="refresh-claims-btn"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Claims Table */}
      <div className="container-card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
          </div>
        ) : filteredClaims.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <FileText className="h-12 w-12 text-[#E2E2DF] mb-4" />
            <p className="text-[#64645F] mb-2">No claims found</p>
            <p className="text-sm text-[#8A8A85]">
              Try adjusting your filters or create a new claim
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead className="w-[140px]">Claim #</TableHead>
                <TableHead>Member</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Service Date</TableHead>
                <TableHead className="text-right">Billed</TableHead>
                <TableHead className="text-right">Paid</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Source</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredClaims.map((claim) => (
                <TableRow 
                  key={claim.id} 
                  className="table-row hover:bg-[#F7F7F4] transition-colors"
                  data-testid={`claim-row-${claim.id}`}
                >
                  <TableCell className="font-['JetBrains_Mono'] text-xs">
                    <Link 
                      to={`/claims/${claim.id}`}
                      className="text-[#1A3636] hover:underline"
                    >
                      {claim.claim_number}
                    </Link>
                    {claim.duplicate_info && (
                      <AlertTriangle className="h-3 w-3 text-[#C24A3B] inline ml-2" />
                    )}
                  </TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs">
                    {claim.member_id}
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">
                    {claim.provider_name}
                  </TableCell>
                  <TableCell className="capitalize">{claim.claim_type}</TableCell>
                  <TableCell>{claim.service_date_from}</TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                    {formatCurrency(claim.total_billed)}
                  </TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#4B6E4E]">
                    {formatCurrency(claim.total_paid)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={claim.status} />
                  </TableCell>
                  <TableCell>
                    {claim.eligibility_source && claim.eligibility_source !== 'standard_hours' ? (
                      <Badge className={
                        claim.eligibility_source === 'bridge_payment' ? 'bg-[#5C2D91] text-white border-0 text-[10px]' :
                        claim.eligibility_source === 'reserve_draw' ? 'bg-[#4A6FA5] text-white border-0 text-[10px]' :
                        claim.eligibility_source === 'insufficient' ? 'bg-[#C24A3B] text-white border-0 text-[10px]' :
                        'bg-[#F0F0EA] text-[#64645F] border-0 text-[10px]'
                      } data-testid={`elig-source-${claim.id}`}>
                        {claim.eligibility_source === 'bridge_payment' ? 'Bridge' :
                         claim.eligibility_source === 'reserve_draw' ? 'Reserve' :
                         claim.eligibility_source === 'insufficient' ? 'Insufficient' :
                         claim.eligibility_source?.replace(/_/g, ' ')}
                      </Badge>
                    ) : (
                      <span className="text-[10px] text-[#8A8A85]">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Link to={`/claims/${claim.id}`}>
                      <Button variant="ghost" size="icon">
                        <ChevronRight className="h-4 w-4 text-[#8A8A85]" />
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between text-sm text-[#64645F]">
        <span>
          Showing {filteredClaims.length} of {claims.length} claims
        </span>
        <span>
          Total Billed: {formatCurrency(filteredClaims.reduce((sum, c) => sum + c.total_billed, 0))}
        </span>
      </div>

      {/* New Claim Modal */}
      <NewClaimModal
        open={showNewClaim}
        onClose={() => setShowNewClaim(false)}
        onSuccess={() => {
          setShowNewClaim(false);
          fetchClaims();
        }}
      />
    </div>
  );
}
