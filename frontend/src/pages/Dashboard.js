import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { dashboardAPI } from '../lib/api';
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
} from 'lucide-react';
import { Button } from '../components/ui/button';
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
