import { useState, useEffect } from 'react';
import { codeAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Search,
  Database,
  RefreshCw,
  Stethoscope,
  Eye,
  Ear,
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

export default function CodeDatabase() {
  const [tab, setTab] = useState('medical');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    codeAPI.dbStats().then((res) => setStats(res.data)).catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      let response;
      switch (tab) {
        case 'dental': response = await codeAPI.searchDental(query); break;
        case 'vision': response = await codeAPI.searchVision(query); break;
        case 'hearing': response = await codeAPI.searchHearing(query); break;
        default: response = await codeAPI.searchCPT(query); break;
      }
      setResults(response.data.results || []);
    } catch (error) {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (query.length >= 2) {
      const t = setTimeout(handleSearch, 400);
      return () => clearTimeout(t);
    } else {
      setResults([]);
    }
  }, [query, tab]);

  const tabConfig = {
    medical: { icon: Stethoscope, label: 'Medical (CPT)', color: 'text-[#1A3636]' },
    dental: { icon: Stethoscope, label: 'Dental (CDT)', color: 'text-[#4B6E4E]' },
    vision: { icon: Eye, label: 'Vision', color: 'text-[#2563EB]' },
    hearing: { icon: Ear, label: 'Hearing', color: 'text-[#C9862B]' },
  };

  return (
    <div className="space-y-6" data-testid="code-database-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">Code Database</h1>
        <p className="text-sm text-[#64645F] mt-1">Search CPT, CDT, vision, and hearing codes across all coverage lines</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="metric-card">
            <p className="metric-label">Medical CPT</p>
            <p className="metric-value">{stats.medical?.total}</p>
            <p className="text-xs text-[#8A8A85] mt-1">{stats.medical?.localities} localities</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Dental CDT</p>
            <p className="metric-value">{stats.dental?.total}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Vision</p>
            <p className="metric-value">{stats.vision?.total}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Hearing</p>
            <p className="metric-value">{stats.hearing?.total}</p>
          </div>
          <div className="metric-card bg-[#1A3636]">
            <p className="text-xs uppercase tracking-wider text-[#a5b4b4] font-medium">Grand Total</p>
            <p className="metric-value text-white">{stats.grand_total}</p>
          </div>
        </div>
      )}

      <Tabs value={tab} onValueChange={(v) => { setTab(v); setResults([]); setQuery(''); }}>
        <TabsList className="bg-[#F0F0EA] border border-[#E2E2DF]" data-testid="code-db-tabs">
          {Object.entries(tabConfig).map(([key, cfg]) => (
            <TabsTrigger key={key} value={key} className="data-[state=active]:bg-white capitalize" data-testid={`tab-${key}`}>
              <cfg.icon className={`h-4 w-4 mr-2 ${cfg.color}`} />{cfg.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {Object.keys(tabConfig).map((key) => (
          <TabsContent key={key} value={key} className="space-y-4">
            <div className="container-card">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
                <Input
                  placeholder={`Search ${key} codes... (e.g., "${key === 'dental' ? 'D1110 or prophylaxis' : key === 'vision' ? '92014 or exam' : key === 'hearing' ? '92557 or audiometry' : '99213 or office visit'}")`}
                  className="input-field pl-10 font-['JetBrains_Mono'] text-sm"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  data-testid={`search-${key}`}
                />
              </div>
            </div>

            <div className="container-card p-0 overflow-hidden">
              {loading ? (
                <div className="flex items-center justify-center h-48"><RefreshCw className="h-6 w-6 text-[#1A3636] animate-spin" /></div>
              ) : results.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center">
                  <Database className="h-10 w-10 text-[#E2E2DF] mb-3" />
                  <p className="text-[#64645F]">{query ? 'No results found' : 'Start typing to search'}</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="table-header">
                      <TableHead>Code</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Category</TableHead>
                      {key === 'medical' && <><TableHead>Work RVU</TableHead><TableHead>Total RVU</TableHead></>}
                      {(key === 'dental' || key === 'vision' || key === 'hearing') && (
                        <><TableHead>Benefit Class</TableHead><TableHead>Fee</TableHead></>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((item) => (
                      <TableRow key={item.code} className="table-row hover:bg-[#F7F7F4] transition-colors" data-testid={`code-row-${item.code}`}>
                        <TableCell className="font-['JetBrains_Mono'] text-xs font-semibold">{item.code}</TableCell>
                        <TableCell className="text-sm max-w-[400px]">{item.description}</TableCell>
                        <TableCell><Badge variant="outline" className="text-xs">{item.category}</Badge></TableCell>
                        {key === 'medical' && (
                          <>
                            <TableCell className="font-['JetBrains_Mono'] text-xs">{item.work_rvu}</TableCell>
                            <TableCell className="font-['JetBrains_Mono'] text-xs">{item.total_rvu}</TableCell>
                          </>
                        )}
                        {(key === 'dental' || key === 'vision' || key === 'hearing') && (
                          <>
                            <TableCell><Badge variant="outline" className="text-xs capitalize">{item.benefit_class?.replace('_', ' ')}</Badge></TableCell>
                            <TableCell className="font-['JetBrains_Mono'] text-xs font-semibold">${item.fee?.toFixed(2)}</TableCell>
                          </>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
