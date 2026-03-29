import { useState, useEffect } from 'react';
import { dashboardAPI, claimsAPI, ediAPI, reportsAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  BarChart3,
  Download,
  RefreshCw,
  FileText,
  Calendar,
  TrendingUp,
  DollarSign,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
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
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  CartesianGrid,
} from 'recharts';

export default function Reports() {
  const [metrics, setMetrics] = useState(null);
  const [claimsByStatus, setClaimsByStatus] = useState([]);
  const [claimsByType, setClaimsByType] = useState([]);
  const [claims, setClaims] = useState([]);
  const [fixedCostData, setFixedCostData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    to: new Date().toISOString().split('T')[0],
  });
  const [generating835, setGenerating835] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [metricsRes, statusRes, typeRes, claimsRes, fixedCostRes] = await Promise.all([
        dashboardAPI.metrics(),
        dashboardAPI.claimsByStatus(),
        dashboardAPI.claimsByType(),
        claimsAPI.list({ limit: 100 }),
        reportsAPI.fixedCostVsClaims(),
      ]);
      
      setMetrics(metricsRes.data);
      setClaimsByStatus(statusRes.data);
      setClaimsByType(typeRes.data);
      setClaims(claimsRes.data);
      setFixedCostData(fixedCostRes.data || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const generate835 = async () => {
    setGenerating835(true);
    try {
      const response = await ediAPI.generate835(dateRange.from, dateRange.to);
      
      const blob = new Blob([response.data.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `835_${dateRange.from}_${dateRange.to}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success(`Generated 835 with ${response.data.claim_count} claims`);
    } catch (error) {
      toast.error('Failed to generate 835');
    } finally {
      setGenerating835(false);
    }
  };

  const exportCSV = () => {
    const headers = ['Claim #', 'Member ID', 'Provider', 'Type', 'Service Date', 'Billed', 'Paid', 'Status'];
    const rows = claims.map((c) => [
      c.claim_number,
      c.member_id,
      c.provider_name,
      c.claim_type,
      c.service_date_from,
      c.total_billed,
      c.total_paid,
      c.status,
    ]);
    
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `claims_report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Report exported');
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value || 0);
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-white border border-[#E2E2DF] rounded-lg p-3 shadow-md text-xs">
        <p className="font-medium text-[#1C1C1A] mb-1">{label}</p>
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="text-[#64645F]">{p.name}:</span>
            <span className="font-['JetBrains_Mono'] font-medium">{formatCurrency(p.value)}</span>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="reports-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Reports & Analytics
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            View insights and export data
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            onClick={exportCSV}
            variant="outline"
            className="btn-secondary"
            data-testid="export-csv-btn"
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Button
            onClick={fetchData}
            variant="outline"
            className="btn-secondary"
            data-testid="refresh-reports-btn"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-[#64645F]" />
            <span className="metric-label">Total Claims</span>
          </div>
          <p className="metric-value">{metrics?.total_claims || 0}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-[#4B6E4E]" />
            <span className="metric-label">Auto-Adjudication</span>
          </div>
          <p className="metric-value text-[#4B6E4E]">
            {metrics?.auto_adjudication_rate || 0}%
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <span className="metric-label">Total Paid</span>
          </div>
          <p className="metric-value">{formatCurrency(metrics?.total_paid)}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <span className="metric-label">Duplicate Savings</span>
          </div>
          <p className="metric-value text-[#C24A3B]">
            {formatCurrency(metrics?.total_saved_duplicates)}
          </p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Claims by Status */}
        <div className="container-card" data-testid="claims-status-chart">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-6">
            Claims by Status
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={claimsByStatus}>
              <XAxis 
                dataKey="status" 
                tick={{ fontSize: 12, fill: '#64645F' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis 
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
              <Bar dataKey="count" fill="#1A3636" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Claims by Type */}
        <div className="container-card" data-testid="claims-type-chart">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-6">
            Claims by Coverage Type
          </h3>
          <ResponsiveContainer width="100%" height={250}>
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
                formatter={(value, name) => {
                  if (name === 'total_paid') return formatCurrency(value);
                  return value;
                }}
              />
              <Bar dataKey="count" fill="#1A3636" radius={[0, 4, 4, 0]} name="Claims" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Fixed Cost vs. Claims Spend Chart */}
      <div className="container-card" data-testid="fixed-cost-vs-claims-chart">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
              Fixed Cost vs. Claims Spend
            </h3>
            <p className="text-xs text-[#8A8A85] mt-1">
              Per-group breakdown of MGU fees, claims paid, and surplus margin
            </p>
          </div>
          <div className="flex items-center gap-4 text-[10px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#C9862B]" />
              <span className="text-[#64645F]">MGU Fees</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#C24A3B]" />
              <span className="text-[#64645F]">Claims Paid</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#4B6E4E]" />
              <span className="text-[#64645F]">Surplus</span>
            </div>
          </div>
        </div>
        {fixedCostData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <DollarSign className="h-8 w-8 text-[#E2E2DF] mb-2" />
            <p className="text-sm text-[#8A8A85]">No group financial data available</p>
            <p className="text-xs text-[#8A8A85]">Create groups with premium & MGU fee data to see this report</p>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={fixedCostData} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E2DF" vertical={false} />
                <XAxis
                  dataKey="group_name"
                  tick={{ fontSize: 11, fill: '#64645F' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#64645F' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="mgu_fees" name="MGU Fees" fill="#C9862B" stackId="costs" radius={[0, 0, 0, 0]} />
                <Bar dataKey="claims_paid" name="Claims Paid" fill="#C24A3B" stackId="costs" radius={[4, 4, 0, 0]} />
                <Bar dataKey="surplus" name="Surplus" fill="#4B6E4E" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            {/* Summary Table */}
            <div className="mt-4 overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead>Group</TableHead>
                    <TableHead className="text-right">Premium</TableHead>
                    <TableHead className="text-right">MGU Fees</TableHead>
                    <TableHead className="text-right">Claims Paid</TableHead>
                    <TableHead className="text-right">Surplus</TableHead>
                    <TableHead className="text-right">Margin</TableHead>
                    <TableHead>Type</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fixedCostData.map((row) => (
                    <TableRow key={row.group_id} className="table-row" data-testid={`fcvc-row-${row.group_id}`}>
                      <TableCell className="font-medium text-sm">{row.group_name}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs">{formatCurrency(row.total_premium)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#C9862B]">{formatCurrency(row.mgu_fees)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#C24A3B]">{formatCurrency(row.claims_paid)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#4B6E4E] font-semibold">{formatCurrency(row.surplus)}</TableCell>
                      <TableCell className="text-right font-['JetBrains_Mono'] text-xs font-semibold">
                        <span className={row.margin_pct > 0 ? 'text-[#4B6E4E]' : 'text-[#C24A3B]'}>{row.margin_pct}%</span>
                      </TableCell>
                      <TableCell>
                        {row.is_mec ? (
                          <Badge className="bg-[#1A3636] text-white text-[10px] border-0">MEC 1</Badge>
                        ) : (
                          <Badge className="bg-[#F0F0EA] text-[#64645F] text-[10px] border-0">Standard</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </div>

      {/* EDI 835 Generation */}
      <div className="container-card" data-testid="edi-835-section">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="h-5 w-5 text-[#64645F]" />
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
            Generate EDI 835
          </h3>
        </div>
        <p className="text-sm text-[#64645F] mb-6">
          Generate an 835 payment file for approved claims within a date range
        </p>
        
        <div className="flex flex-wrap gap-4 items-end">
          <div className="space-y-2">
            <Label>From Date</Label>
            <Input
              type="date"
              value={dateRange.from}
              onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
              className="input-field w-40"
              data-testid="835-date-from"
            />
          </div>
          <div className="space-y-2">
            <Label>To Date</Label>
            <Input
              type="date"
              value={dateRange.to}
              onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
              className="input-field w-40"
              data-testid="835-date-to"
            />
          </div>
          <Button
            onClick={generate835}
            disabled={generating835}
            className="btn-primary"
            data-testid="generate-835-btn"
          >
            {generating835 ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Generate 835
          </Button>
        </div>
      </div>

      {/* Claims Summary Table */}
      <div className="container-card p-0 overflow-hidden" data-testid="claims-summary-table">
        <div className="p-6 border-b border-[#E2E2DF]">
          <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
            Claims Summary
          </h3>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>Coverage Type</TableHead>
                <TableHead className="text-right">Claims</TableHead>
                <TableHead className="text-right">Total Billed</TableHead>
                <TableHead className="text-right">Total Paid</TableHead>
                <TableHead className="text-right">Avg Payment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {claimsByType.map((item) => (
                <TableRow key={item.type} className="table-row">
                  <TableCell className="font-medium capitalize">{item.type}</TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                    {item.count}
                  </TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                    {formatCurrency(item.total_billed)}
                  </TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#4B6E4E]">
                    {formatCurrency(item.total_paid)}
                  </TableCell>
                  <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                    {formatCurrency(item.count > 0 ? item.total_paid / item.count : 0)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
