import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { dashboardAPI } from '../lib/api';
import { examinerAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Activity,
  ArrowRight,
  RefreshCw,
  Building2,
  CreditCard,
  Wallet,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

const STATUS_COLORS = {
  pending: '#C9862B',
  in_review: '#4A6FA5',
  approved: '#4B6E4E',
  denied: '#C24A3B',
  duplicate: '#C24A3B',
  pended: '#4A6FA5',
  managerial_hold: '#5C2D91',
  pending_review: '#C24A3B',
  pending_eligibility: '#C9862B',
};

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [claimsByStatus, setClaimsByStatus] = useState([]);
  const [claimsByType, setClaimsByType] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [examinerPerf, setExaminerPerf] = useState([]);
  const [fundingHealth, setFundingHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [metricsRes, statusRes, typeRes, activityRes] = await Promise.all([
        dashboardAPI.metrics(),
        dashboardAPI.claimsByStatus(),
        dashboardAPI.claimsByType(),
        dashboardAPI.recentActivity(5),
      ]);
      
      setMetrics(metricsRes.data);
      setClaimsByStatus(statusRes.data);
      setClaimsByType(typeRes.data);
      setRecentActivity(activityRes.data);
      
      // Fetch examiner performance
      try {
        const perfRes = await examinerAPI.performance();
        setExaminerPerf(perfRes.data);
      } catch {}
      // Fetch funding health
      try {
        const fhRes = await dashboardAPI.fundingHealth();
        setFundingHealth(fhRes.data);
      } catch {}
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value || 0);
  };

  const formatNumber = (value) => {
    return new Intl.NumberFormat('en-US').format(value || 0);
  };

  const getActivityIcon = (action) => {
    if (action.includes('claim_approved')) return <CheckCircle2 className="h-4 w-4 text-[#4B6E4E]" />;
    if (action.includes('claim_denied')) return <XCircle className="h-4 w-4 text-[#C24A3B]" />;
    if (action.includes('claim')) return <FileText className="h-4 w-4 text-[#4A6FA5]" />;
    if (action.includes('plan')) return <Activity className="h-4 w-4 text-[#8E9F85]" />;
    return <Clock className="h-4 w-4 text-[#64645F]" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
      </div>
    );
  }

  const pieData = claimsByStatus.map((item) => ({
    name: item.status,
    value: item.count,
    color: STATUS_COLORS[item.status] || '#8A8A85',
  }));

  return (
    <div className="space-y-8" data-testid="dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Dashboard
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            Overview of your claims adjudication system
          </p>
        </div>
        <Button
          onClick={fetchDashboardData}
          variant="outline"
          className="btn-secondary"
          data-testid="refresh-dashboard-btn"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Duplicate Alert Banner */}
      {metrics?.duplicate_alerts > 0 && (
        <div 
          className="bg-[#FBEAE7] border border-[#C24A3B]/30 rounded-xl p-4 flex items-center justify-between duplicate-alert-pulse"
          data-testid="duplicate-alert-banner"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#C24A3B] rounded-lg flex items-center justify-center">
              <AlertTriangle className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#C24A3B]">
                {metrics.duplicate_alerts} Duplicate Alert{metrics.duplicate_alerts !== 1 ? 's' : ''} Pending Review
              </p>
              <p className="text-xs text-[#64645F]">
                Claims flagged as potential duplicates require your attention
              </p>
            </div>
          </div>
          <Link to="/duplicates">
            <Button className="btn-destructive" data-testid="view-duplicates-btn">
              Review Now
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </div>
      )}

      {/* Held Claims Banner */}
      {metrics?.held_claims > 0 && (
        <div 
          className="bg-[#F3EBF9] border border-[#5C2D91]/30 rounded-xl p-4 flex items-center justify-between"
          data-testid="held-claims-banner"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#5C2D91] rounded-lg flex items-center justify-center">
              <Clock className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#5C2D91]">
                {metrics.held_claims} Claim{metrics.held_claims !== 1 ? 's' : ''} on Managerial Hold
              </p>
              <p className="text-xs text-[#64645F]">
                Frozen claims excluded from financials — requires admin release
              </p>
            </div>
          </div>
          <Link to="/claims">
            <Button className="bg-[#5C2D91] hover:bg-[#4a2475] text-white" data-testid="view-held-btn">
              Review
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="metric-card" data-testid="metric-total-claims">
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-[#EEF3F9] rounded-lg flex items-center justify-center">
              <FileText className="h-5 w-5 text-[#4A6FA5]" />
            </div>
            <span className="text-xs text-[#4B6E4E] font-medium bg-[#EDF2EE] px-2 py-1 rounded">
              +12.5%
            </span>
          </div>
          <p className="metric-value">{formatNumber(metrics?.total_claims)}</p>
          <p className="metric-label mt-1">Total Claims</p>
        </div>

        <div className="metric-card" data-testid="metric-pending-claims">
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-[#FDF3E1] rounded-lg flex items-center justify-center">
              <Clock className="h-5 w-5 text-[#C9862B]" />
            </div>
          </div>
          <p className="metric-value">{formatNumber(metrics?.pending_claims)}</p>
          <p className="metric-label mt-1">Pending Review</p>
        </div>

        <div className="metric-card" data-testid="metric-total-paid">
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-[#EDF2EE] rounded-lg flex items-center justify-center">
              <DollarSign className="h-5 w-5 text-[#4B6E4E]" />
            </div>
          </div>
          <p className="metric-value">{formatCurrency(metrics?.total_paid)}</p>
          <p className="metric-label mt-1">Total Paid</p>
        </div>

        <div className="metric-card" data-testid="metric-duplicate-savings">
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-[#FBEAE7] rounded-lg flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-[#C24A3B]" />
            </div>
          </div>
          <p className="metric-value">{formatCurrency(metrics?.total_saved_duplicates)}</p>
          <p className="metric-label mt-1">Duplicate Savings</p>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="container-card" data-testid="metric-auto-adjudication">
          <div className="flex items-center justify-between">
            <div>
              <p className="metric-label">Auto-Adjudication Rate</p>
              <p className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit'] mt-1">
                {metrics?.auto_adjudication_rate || 0}%
              </p>
            </div>
            <div className="w-16 h-16">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { value: metrics?.auto_adjudication_rate || 0 },
                      { value: 100 - (metrics?.auto_adjudication_rate || 0) },
                    ]}
                    dataKey="value"
                    cx="50%"
                    cy="50%"
                    innerRadius={18}
                    outerRadius={28}
                    startAngle={90}
                    endAngle={-270}
                  >
                    <Cell fill="#1A3636" />
                    <Cell fill="#E2E2DF" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="container-card" data-testid="metric-turnaround">
          <p className="metric-label">Avg Turnaround Time</p>
          <p className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit'] mt-1">
            {metrics?.avg_turnaround_hours || 0} hrs
          </p>
          <p className="text-xs text-[#4B6E4E] mt-2">Below 24hr target</p>
        </div>

        <div className="container-card" data-testid="metric-approved-denied">
          <p className="metric-label">Approved / Denied</p>
          <div className="flex items-center gap-4 mt-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-[#4B6E4E]" />
              <span className="text-xl font-semibold text-[#1C1C1A] font-['Outfit']">
                {formatNumber(metrics?.approved_claims)}
              </span>
            </div>
            <div className="w-px h-6 bg-[#E2E2DF]" />
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-[#C24A3B]" />
              <span className="text-xl font-semibold text-[#1C1C1A] font-['Outfit']">
                {formatNumber(metrics?.denied_claims)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Funding Health Widget */}
      {fundingHealth && (fundingHealth.aso.group_count > 0 || fundingHealth.level_funded.group_count > 0) && (
        <div className="container-card" data-testid="funding-health-widget">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#F3EBF9] rounded-lg flex items-center justify-center">
                <Wallet className="h-5 w-5 text-[#5C2D91]" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Funding Health</h3>
                <p className="text-[10px] text-[#8A8A85]">Real-time financial overview by funding model</p>
              </div>
            </div>
            <Link to="/check-runs">
              <Button variant="outline" size="sm" className="text-xs">
                <CreditCard className="h-3 w-3 mr-1" />Check Runs
              </Button>
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* ASO */}
            {fundingHealth.aso.group_count > 0 && (
              <div className="bg-[#EFF4FB] rounded-xl p-4 border border-[#C8D8EE]" data-testid="funding-aso">
                <div className="flex items-center gap-2 mb-3">
                  <Badge className="bg-[#4A6FA5] text-white border-0 text-[10px]">ASO</Badge>
                  <span className="text-xs text-[#8A8A85]">{fundingHealth.aso.group_count} groups</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-[#64645F]">Pending Funding</span>
                    <span className="font-['JetBrains_Mono'] font-semibold text-[#C9862B]" data-testid="aso-pending">{formatCurrency(fundingHealth.aso.pending_funding)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[#64645F]">Total Paid</span>
                    <span className="font-['JetBrains_Mono'] font-semibold text-[#4B6E4E]" data-testid="aso-paid">{formatCurrency(fundingHealth.aso.total_paid)}</span>
                  </div>
                </div>
              </div>
            )}
            {/* Level Funded */}
            {fundingHealth.level_funded.group_count > 0 && (
              <div className="bg-[#F9F5FF] rounded-xl p-4 border border-[#D8C8E8]" data-testid="funding-level-funded">
                <div className="flex items-center gap-2 mb-3">
                  <Badge className="bg-[#5C2D91] text-white border-0 text-[10px]">Level Funded</Badge>
                  <span className="text-xs text-[#8A8A85]">{fundingHealth.level_funded.group_count} groups</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-[#64645F]">Expected Fund</span>
                    <span className="font-['JetBrains_Mono'] font-semibold" data-testid="lf-expected">{formatCurrency(fundingHealth.level_funded.expected_fund)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[#64645F]">Actual Claims</span>
                    <span className="font-['JetBrains_Mono'] font-semibold text-[#C24A3B]" data-testid="lf-actual">{formatCurrency(fundingHealth.level_funded.actual_claims)}</span>
                  </div>
                  <div className="flex justify-between text-sm border-t border-[#D8C8E8] pt-2">
                    <span className="text-[#64645F] font-medium">Surplus</span>
                    <span className={`font-['JetBrains_Mono'] font-semibold ${fundingHealth.level_funded.surplus >= 0 ? 'text-[#4B6E4E]' : 'text-[#C24A3B]'}`} data-testid="lf-surplus">{formatCurrency(fundingHealth.level_funded.surplus)}</span>
                  </div>
                </div>
                {fundingHealth.level_funded.deficit_groups?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#D8C8E8]">
                    <div className="flex items-center gap-1 text-xs text-[#C24A3B] mb-1"><AlertTriangle className="h-3 w-3" />Deficit Groups:</div>
                    {fundingHealth.level_funded.deficit_groups.map(dg => (
                      <Badge key={dg.group_id} className="bg-[#FBEAE7] text-[#C24A3B] border-0 text-[10px] mr-1">{dg.group_name}: {formatCurrency(dg.deficit)}</Badge>
                    ))}
                  </div>
                )}
              </div>
            )}
            {/* Fully Insured */}
            {fundingHealth.fully_insured.group_count > 0 && (
              <div className="bg-[#F0F7F1] rounded-xl p-4 border border-[#D4E5D6]" data-testid="funding-fully-insured">
                <div className="flex items-center gap-2 mb-3">
                  <Badge className="bg-[#1A3636] text-white border-0 text-[10px]">Fully Insured</Badge>
                  <span className="text-xs text-[#8A8A85]">{fundingHealth.fully_insured.group_count} groups</span>
                </div>
                <p className="text-sm text-[#64645F]">Carrier-managed risk. No employer-level reserve tracking required.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Claims by Status */}
        <div className="container-card" data-testid="claims-by-status-chart">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-6">
            Claims by Status
          </h3>
          <div className="flex items-center gap-8">
            <div className="w-40 h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-3">
              {claimsByStatus.map((item) => (
                <div key={item.status} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[item.status] || '#8A8A85' }}
                    />
                    <span className="text-sm text-[#64645F] capitalize">
                      {item.status.replace('_', ' ')}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-[#1C1C1A] font-['JetBrains_Mono']">
                    {item.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Claims by Type */}
        <div className="container-card" data-testid="claims-by-type-chart">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-6">
            Claims by Coverage Type
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={claimsByType} layout="vertical">
              <XAxis type="number" hide />
              <YAxis 
                type="category" 
                dataKey="type" 
                width={80}
                tick={{ fontSize: 12, fill: '#64645F' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #E2E2DF',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="count" fill="#1A3636" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Examiner Performance Widget */}
      {examinerPerf.length > 0 && (
        <div className="container-card" data-testid="examiner-performance">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
              Examiner Performance
            </h3>
            <Link to="/examiner-queue" className="text-sm text-[#1A3636] hover:text-[#2A4B4B] font-medium">
              Open Queue
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {examinerPerf.map((ex) => (
              <div key={ex.examiner_id} className="bg-[#F7F7F4] rounded-lg p-4" data-testid={`perf-${ex.examiner_id}`}>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-[#1C1C1A] truncate">{ex.examiner_name}</p>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${ex.role === 'admin' ? 'bg-[#1A3636] text-white' : 'bg-[#F0F0EA] text-[#64645F]'}`}>
                    {ex.role === 'admin' ? 'Senior' : 'Junior'}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <p className="text-[10px] text-[#8A8A85] uppercase">Open</p>
                    <p className="text-lg font-semibold font-['Outfit'] text-[#1C1C1A]">{ex.open_claims}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#8A8A85] uppercase">Closed Today</p>
                    <p className="text-lg font-semibold font-['Outfit'] text-[#4B6E4E]">{ex.closed_today}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#8A8A85] uppercase">Avg TAT</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono'] text-[#C9862B]">{ex.avg_tat_hours}h</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="container-card" data-testid="recent-activity">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
            Recent Activity
          </h3>
          <Link to="/claims" className="text-sm text-[#1A3636] hover:text-[#2A4B4B] font-medium">
            View all claims
          </Link>
        </div>
        <div className="space-y-4">
          {recentActivity.length === 0 ? (
            <p className="text-sm text-[#64645F] text-center py-8">No recent activity</p>
          ) : (
            recentActivity.map((activity) => (
              <div
                key={activity.id}
                className="flex items-center gap-4 p-3 rounded-lg hover:bg-[#F7F7F4] transition-colors"
              >
                <div className="w-8 h-8 bg-[#F0F0EA] rounded-lg flex items-center justify-center">
                  {getActivityIcon(activity.action)}
                </div>
                <div className="flex-1">
                  <p className="text-sm text-[#1C1C1A]">
                    <span className="font-medium capitalize">
                      {activity.action.replace(/_/g, ' ')}
                    </span>
                    {activity.details?.claim_number && (
                      <span className="text-[#64645F]">
                        {' '}• Claim{' '}
                        <span className="font-['JetBrains_Mono'] text-xs">
                          {activity.details.claim_number}
                        </span>
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-[#8A8A85]">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
