import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { toast } from 'sonner';
import {
  Search,
  Heart,
  RefreshCw,
  Shield,
  Baby,
  Syringe,
  Eye,
  Brain,
  Activity,
  Users,
  BarChart3,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';

const CATEGORY_CONFIG = {
  'Wellness Visit': { icon: Heart, color: 'text-[#4B6E4E]', bg: 'bg-[#4B6E4E]/10' },
  'Immunization': { icon: Syringe, color: 'text-[#2563EB]', bg: 'bg-[#2563EB]/10' },
  'Cancer Screening': { icon: Shield, color: 'text-[#C24A3B]', bg: 'bg-[#C24A3B]/10' },
  'Preventive Screening': { icon: Activity, color: 'text-[#C9862B]', bg: 'bg-[#C9862B]/10' },
  "Women's Preventive": { icon: Users, color: 'text-[#9333EA]', bg: 'bg-[#9333EA]/10' },
  'Pediatric Preventive': { icon: Baby, color: 'text-[#0891B2]', bg: 'bg-[#0891B2]/10' },
  'Behavioral Counseling': { icon: Brain, color: 'text-[#D97706]', bg: 'bg-[#D97706]/10' },
};

export default function PreventiveServices() {
  const [tab, setTab] = useState('catalog');
  const [categories, setCategories] = useState({});
  const [services, setServices] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [abuseFlags, setAbuseFlags] = useState([]);
  const [query, setQuery] = useState('');
  const [expandedCat, setExpandedCat] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await api.get('/preventive/categories');
      setCategories(res.data);
    } catch { /* ignore */ }
  }, []);

  const fetchAnalytics = useCallback(async () => {
    try {
      const res = await api.get('/preventive/analytics');
      setAnalytics(res.data);
    } catch { /* ignore */ }
  }, []);

  const fetchAbuse = useCallback(async () => {
    try {
      const res = await api.get('/preventive/abuse-detection');
      setAbuseFlags(res.data.flags || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchCategories(), fetchAnalytics(), fetchAbuse()]).finally(() => setLoading(false));
  }, [fetchCategories, fetchAnalytics, fetchAbuse]);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) { setServices([]); return; }
    try {
      const res = await api.get('/preventive/search', { params: { q: query } });
      setServices(res.data.results || []);
    } catch { toast.error('Search failed'); }
  }, [query]);

  useEffect(() => {
    if (query.length >= 2) {
      const t = setTimeout(handleSearch, 400);
      return () => clearTimeout(t);
    } else { setServices([]); }
  }, [query, handleSearch]);

  const loadCategory = async (cat) => {
    if (expandedCat === cat) { setExpandedCat(null); return; }
    try {
      const res = await api.get('/preventive/services', { params: { category: cat } });
      setServices(res.data.results || []);
      setExpandedCat(cat);
    } catch { toast.error('Failed to load category'); }
  };

  const formatFrequency = (svc) => {
    const period = svc.frequency_period || '';
    const limit = svc.frequency_limit || 1;
    const map = {
      'year': `${limit}/year`,
      '3_years': `${limit}/3 years`,
      '5_years': `${limit}/5 years`,
      '10_years': `${limit}/10 years`,
      'lifetime': `${limit}/lifetime`,
      'pregnancy': `${limit}/pregnancy`,
    };
    return map[period] || `${limit}/${period}`;
  };

  const formatAge = (svc) => {
    const min = svc.age_min ?? 0;
    const max = svc.age_max ?? 999;
    if (min === 0 && max >= 999) return 'All ages';
    if (max >= 999) return `${min}+`;
    return `${min}-${max}`;
  };

  return (
    <div className="space-y-6" data-testid="preventive-services-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Preventive Services</h1>
        <p className="text-sm text-[#64645F] mt-1">ACA-compliant preventive care rules, frequency limits, and utilization analytics</p>
      </div>

      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="metric-card">
            <p className="metric-label">Total Codes</p>
            <p className="metric-value">{analytics.total_preventive_codes}</p>
            <p className="text-xs text-[#8A8A85] mt-1">7 categories</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Services Used</p>
            <p className="metric-value">{analytics.total_preventive_services}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Members w/ Preventive</p>
            <p className="metric-value">{analytics.members_with_preventive}/{analytics.total_active_members}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Compliance Rate</p>
            <p className="metric-value text-[#4B6E4E]">{analytics.compliance_rate}%</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Preventive PMPM</p>
            <p className="metric-value">${analytics.preventive_pmpm}</p>
          </div>
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF]" data-testid="preventive-tabs">
          <TabsTrigger value="catalog" className="data-[state=active]:bg-white" data-testid="tab-catalog">
            <Heart className="h-4 w-4 mr-2 text-[#4B6E4E]" />Catalog
          </TabsTrigger>
          <TabsTrigger value="analytics" className="data-[state=active]:bg-white" data-testid="tab-analytics">
            <BarChart3 className="h-4 w-4 mr-2 text-[#C9862B]" />Analytics
          </TabsTrigger>
          <TabsTrigger value="abuse" className="data-[state=active]:bg-white" data-testid="tab-abuse">
            <Shield className="h-4 w-4 mr-2 text-[#C24A3B]" />Abuse Detection
          </TabsTrigger>
        </TabsList>

        {/* CATALOG TAB */}
        <TabsContent value="catalog" className="space-y-4">
          <div className="container-card">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
              <Input
                placeholder='Search preventive services... (e.g., "mammogram", "colonoscopy", "99395", "HPV")'
                className="input-field pl-10 font-['JetBrains_Mono'] text-sm"
                value={query}
                onChange={(e) => { setQuery(e.target.value); setExpandedCat(null); }}
                data-testid="preventive-search"
              />
            </div>
          </div>

          {query.length >= 2 ? (
            <ServiceTable services={services} formatFrequency={formatFrequency} formatAge={formatAge} />
          ) : (
            <div className="space-y-3">
              {Object.entries(categories).map(([cat, info]) => {
                const cfg = CATEGORY_CONFIG[cat] || { icon: Heart, color: 'text-[#64645F]', bg: 'bg-[#F0F0EA]' };
                const Icon = cfg.icon;
                const isExpanded = expandedCat === cat;
                return (
                  <div key={cat}>
                    <button
                      onClick={() => loadCategory(cat)}
                      className="w-full container-card flex items-center justify-between hover:bg-[#F7F7F4] transition-colors cursor-pointer"
                      data-testid={`cat-${cat.replace(/[^a-zA-Z]/g, '-').toLowerCase()}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2.5 rounded-xl ${cfg.bg}`}>
                          <Icon className={`h-5 w-5 ${cfg.color}`} />
                        </div>
                        <div className="text-left">
                          <h3 className="font-medium text-[#1C1C1A] font-['Outfit']">{cat}</h3>
                          <p className="text-xs text-[#8A8A85] mt-0.5">
                            {info.count} services {info.subcategories?.length > 0 && `- ${info.subcategories.join(', ')}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge className={`${cfg.bg} ${cfg.color} border-0 font-mono text-xs`}>{info.count}</Badge>
                        {isExpanded ? <ChevronDown className="h-4 w-4 text-[#8A8A85]" /> : <ChevronRight className="h-4 w-4 text-[#8A8A85]" />}
                      </div>
                    </button>
                    {isExpanded && <ServiceTable services={services} formatFrequency={formatFrequency} formatAge={formatAge} />}
                  </div>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* ANALYTICS TAB */}
        <TabsContent value="analytics" className="space-y-4">
          {analytics && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="container-card">
                  <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Utilization Summary</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Total Preventive Services</span>
                      <span className="font-semibold">{analytics.total_preventive_services}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Claims with Preventive</span>
                      <span className="font-semibold">{analytics.claims_with_preventive}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Total Preventive Paid</span>
                      <span className="font-semibold font-['JetBrains_Mono']">${analytics.total_preventive_paid?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Preventive PMPM</span>
                      <span className="font-semibold font-['JetBrains_Mono']">${analytics.preventive_pmpm}</span>
                    </div>
                  </div>
                </div>
                <div className="container-card">
                  <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Compliance</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Active Members</span>
                      <span className="font-semibold">{analytics.total_active_members}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Members w/ Annual Visit</span>
                      <span className="font-semibold">{analytics.members_with_preventive}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#64645F]">Compliance Rate</span>
                      <span className="font-semibold text-[#4B6E4E]">{analytics.compliance_rate}%</span>
                    </div>
                    <div className="w-full h-3 bg-[#F0F0EA] rounded-full overflow-hidden mt-2">
                      <div className="h-full bg-[#4B6E4E] rounded-full transition-all" style={{ width: `${Math.min(100, analytics.compliance_rate)}%` }} />
                    </div>
                  </div>
                </div>
                <div className="container-card">
                  <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Category Breakdown</h3>
                  {analytics.category_breakdown?.length === 0 ? (
                    <p className="text-sm text-[#8A8A85]">No utilization data yet</p>
                  ) : (
                    <div className="space-y-2">
                      {analytics.category_breakdown?.map((cat) => {
                        const cfg = CATEGORY_CONFIG[cat.category] || {};
                        return (
                          <div key={cat.category} className="flex justify-between items-center text-sm">
                            <span className="text-[#64645F] truncate max-w-[180px]">{cat.category}</span>
                            <Badge className={`${cfg.bg || 'bg-[#F0F0EA]'} ${cfg.color || ''} border-0 font-mono text-xs`}>{cat.count}</Badge>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </TabsContent>

        {/* ABUSE DETECTION TAB */}
        <TabsContent value="abuse" className="space-y-4">
          <div className="container-card p-0 overflow-hidden">
            <div className="p-6 border-b border-[#E2E2DF]">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Abuse & Fraud Flags</h3>
              <p className="text-xs text-[#8A8A85] mt-1">Duplicate visits, excess frequency, unrelated diagnoses</p>
            </div>
            {loading ? (
              <div className="flex items-center justify-center h-48"><RefreshCw className="h-6 w-6 text-[#1A3636] animate-spin" /></div>
            ) : abuseFlags.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <Shield className="h-10 w-10 text-[#4B6E4E] mb-3" />
                <p className="text-[#64645F] font-medium">No abuse flags detected</p>
                <p className="text-xs text-[#8A8A85] mt-1">All preventive utilization appears within normal patterns</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead>Type</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Member</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {abuseFlags.map((flag, i) => (
                    <TableRow key={i} className="table-row hover:bg-[#F7F7F4]">
                      <TableCell className="text-xs capitalize">{flag.type?.replace(/_/g, ' ')}</TableCell>
                      <TableCell>
                        <Badge className={flag.severity === 'high' ? 'badge-denied' : 'badge-pended'}>{flag.severity}</Badge>
                      </TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-xs">{flag.member_id}</TableCell>
                      <TableCell className="text-sm max-w-[300px] truncate">{flag.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ServiceTable({ services, formatFrequency, formatAge }) {
  if (!services || services.length === 0) {
    return (
      <div className="container-card flex items-center justify-center h-24">
        <p className="text-sm text-[#8A8A85]">No services found</p>
      </div>
    );
  }
  return (
    <div className="container-card p-0 overflow-hidden mt-2">
      <Table>
        <TableHeader>
          <TableRow className="table-header">
            <TableHead>Code</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Age</TableHead>
            <TableHead>Gender</TableHead>
            <TableHead>Frequency</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Fee</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {services.map((svc) => (
            <TableRow key={svc.code} className="table-row hover:bg-[#F7F7F4] transition-colors" data-testid={`prev-row-${svc.code}`}>
              <TableCell className="font-['JetBrains_Mono'] text-xs font-semibold">{svc.code}</TableCell>
              <TableCell className="text-sm max-w-[300px]">{svc.description}</TableCell>
              <TableCell><Badge variant="outline" className="text-xs">{svc.subcategory || svc.category}</Badge></TableCell>
              <TableCell className="text-xs font-['JetBrains_Mono']">{formatAge(svc)}</TableCell>
              <TableCell className="text-xs capitalize">{svc.gender === 'all' ? 'All' : svc.gender}</TableCell>
              <TableCell className="text-xs font-['JetBrains_Mono']">{formatFrequency(svc)}</TableCell>
              <TableCell><Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-xs">{svc.source}</Badge></TableCell>
              <TableCell className="font-['JetBrains_Mono'] text-xs font-semibold">{svc.fee > 0 ? `$${svc.fee?.toFixed(2)}` : '$0.00'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
