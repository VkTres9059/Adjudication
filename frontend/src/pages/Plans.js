import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { plansAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Plus,
  Search,
  Building2,
  RefreshCw,
  Edit,
  Copy,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const STATUS_CONFIG = {
  active: { label: 'Active', icon: CheckCircle2, class: 'badge-approved' },
  inactive: { label: 'Inactive', icon: XCircle, class: 'badge-denied' },
  draft: { label: 'Draft', icon: Clock, class: 'badge-pending' },
};

export default function Plans() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.plan_type = typeFilter;
      
      const response = await plansAPI.list(params);
      setPlans(response.data);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
      toast.error('Failed to load plans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, [statusFilter, typeFilter]);

  const filteredPlans = plans.filter((plan) => {
    if (!search) return true;
    return (
      plan.name.toLowerCase().includes(search.toLowerCase()) ||
      plan.group_id.toLowerCase().includes(search.toLowerCase())
    );
  });

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value || 0);
  };

  const StatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
    const Icon = config.icon;
    return (
      <Badge className={`${config.class} flex items-center gap-1.5`}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  return (
    <div className="space-y-6" data-testid="plans-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Benefit Plans
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            Manage plan configurations and benefits
          </p>
        </div>
        <Link to="/plans/new">
          <Button className="btn-primary" data-testid="new-plan-btn">
            <Plus className="h-4 w-4 mr-2" />
            Create Plan
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="container-card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
            <Input
              placeholder="Search plans..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 input-field"
              data-testid="plans-search-input"
            />
          </div>
          <div className="flex gap-3">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-36" data-testid="status-filter">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-36" data-testid="type-filter">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                <SelectItem value="medical">Medical</SelectItem>
                <SelectItem value="dental">Dental</SelectItem>
                <SelectItem value="vision">Vision</SelectItem>
                <SelectItem value="hearing">Hearing</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              onClick={fetchPlans}
              className="btn-secondary"
              data-testid="refresh-plans-btn"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Plans Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
        </div>
      ) : filteredPlans.length === 0 ? (
        <div className="container-card flex flex-col items-center justify-center h-64 text-center">
          <Building2 className="h-12 w-12 text-[#E2E2DF] mb-4" />
          <p className="text-[#64645F] mb-2">No plans found</p>
          <p className="text-sm text-[#8A8A85]">
            Create your first benefit plan to get started
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPlans.map((plan) => (
            <div
              key={plan.id}
              className="container-card card-hover"
              data-testid={`plan-card-${plan.id}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-medium text-[#1C1C1A] font-['Outfit']">
                    {plan.name}
                  </h3>
                  <p className="text-xs text-[#8A8A85] font-['JetBrains_Mono'] mt-1">
                    {plan.group_id}
                  </p>
                </div>
                <StatusBadge status={plan.status} />
              </div>

              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[#64645F]">Type</span>
                  <span className="font-medium capitalize">{plan.plan_type}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[#64645F]">Network</span>
                  <span className="font-medium">{plan.network_type}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[#64645F]">Deductible</span>
                  <span className="font-medium font-['JetBrains_Mono'] text-xs">
                    {formatCurrency(plan.deductible_individual)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[#64645F]">OOP Max</span>
                  <span className="font-medium font-['JetBrains_Mono'] text-xs">
                    {formatCurrency(plan.oop_max_individual)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[#64645F]">Effective</span>
                  <span className="font-medium">{plan.effective_date}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-[#E2E2DF]">
                <div className="text-xs text-[#8A8A85]">
                  v{plan.version} • {plan.benefits?.length || 0} benefits
                </div>
                <div className="flex gap-1">
                  <Link to={`/plans/${plan.id}/edit`}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:bg-[#F0F0EA]"
                      data-testid={`edit-plan-${plan.id}`}
                    >
                      <Edit className="h-4 w-4 text-[#64645F]" />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 hover:bg-[#F0F0EA]"
                    data-testid={`clone-plan-${plan.id}`}
                  >
                    <Copy className="h-4 w-4 text-[#64645F]" />
                  </Button>
                  <Link to={`/plans/${plan.id}/edit`}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:bg-[#F0F0EA]"
                    >
                      <ChevronRight className="h-4 w-4 text-[#64645F]" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="text-sm text-[#64645F]">
        Showing {filteredPlans.length} of {plans.length} plans
      </div>
    </div>
  );
}
