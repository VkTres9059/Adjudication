import { useState, useEffect } from 'react';
import api from '../lib/api';
import { toast } from 'sonner';
import {
  Search,
  RefreshCw,
  Calculator,
  MapPin,
  FileText,
  DollarSign,
  Info,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
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
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';

const CATEGORY_COLORS = {
  'E/M': 'bg-[#1A3636] text-white',
  'Anesthesia': 'bg-[#4A6FA5] text-white',
  'Surgery': 'bg-[#C24A3B] text-white',
  'Radiology': 'bg-[#8E9F85] text-white',
  'Pathology/Lab': 'bg-[#C9862B] text-white',
  'Medicine': 'bg-[#4B6E4E] text-white',
  'HCPCS': 'bg-[#64645F] text-white',
};

export default function FeeSchedule() {
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [localities, setLocalities] = useState([]);
  const [selectedLocality, setSelectedLocality] = useState('00000');
  const [selectedCode, setSelectedCode] = useState(null);
  const [rateDetails, setRateDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showCodeDetail, setShowCodeDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('search');

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [statsRes, localitiesRes] = await Promise.all([
        api.get('/fee-schedule/stats'),
        api.get('/fee-schedule/localities'),
      ]);
      setStats(statsRes.data);
      setLocalities(localitiesRes.data.localities);
    } catch (error) {
      console.error('Failed to fetch fee schedule data:', error);
      toast.error('Failed to load fee schedule data');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setSearchLoading(true);
    try {
      const response = await api.get(`/cpt-codes/search?q=${encodeURIComponent(searchQuery)}&limit=50`);
      setSearchResults(response.data.results);
      if (response.data.results.length === 0) {
        toast.info('No CPT codes found matching your search');
      }
    } catch (error) {
      console.error('Failed to search CPT codes:', error);
      toast.error('Failed to search CPT codes');
    } finally {
      setSearchLoading(false);
    }
  };

  const handleCodeClick = async (code) => {
    setSelectedCode(code);
    setShowCodeDetail(true);
    
    try {
      const response = await api.get(`/fee-schedule/rate?cpt_code=${code.code}&locality=${selectedLocality}`);
      setRateDetails(response.data);
    } catch (error) {
      console.error('Failed to fetch rate details:', error);
      toast.error('Failed to calculate rate');
    }
  };

  const handleLocalityChange = async (locality) => {
    setSelectedLocality(locality);
    if (selectedCode) {
      try {
        const response = await api.get(`/fee-schedule/rate?cpt_code=${selectedCode.code}&locality=${locality}`);
        setRateDetails(response.data);
      } catch (error) {
        console.error('Failed to recalculate rate:', error);
      }
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value || 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="fee-schedule-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Medicare Fee Schedule
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            CPT codes and Medicare reimbursement rates with GPCI adjustments
          </p>
        </div>
        <Button
          onClick={fetchInitialData}
          variant="outline"
          className="btn-secondary"
          data-testid="refresh-fee-schedule-btn"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-[#64645F]" />
            <span className="metric-label">CPT Codes</span>
          </div>
          <p className="metric-value">{stats?.total_cpt_codes || 0}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="h-4 w-4 text-[#64645F]" />
            <span className="metric-label">GPCI Localities</span>
          </div>
          <p className="metric-value">{stats?.total_localities || 0}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <Calculator className="h-4 w-4 text-[#64645F]" />
            <span className="metric-label">2024 Conversion Factor</span>
          </div>
          <p className="metric-value">${stats?.conversion_factor_2024 || 0}</p>
        </div>
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <span className="metric-label">Categories</span>
          </div>
          <p className="metric-value">{Object.keys(stats?.categories || {}).length}</p>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="container-card">
        <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">
          CPT Codes by Category
        </h3>
        <div className="flex flex-wrap gap-3">
          {stats?.category_counts?.map((cat) => (
            <div
              key={cat.category}
              className="flex items-center gap-2 px-3 py-2 bg-[#F7F7F4] rounded-lg"
            >
              <Badge className={CATEGORY_COLORS[cat.category] || 'bg-[#64645F] text-white'}>
                {cat.category}
              </Badge>
              <span className="text-sm font-medium text-[#1C1C1A]">{cat.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-[#F0F0EA] p-1">
          <TabsTrigger value="search" data-testid="tab-search">
            <Search className="h-4 w-4 mr-2" />
            Search Codes
          </TabsTrigger>
          <TabsTrigger value="localities" data-testid="tab-localities">
            <MapPin className="h-4 w-4 mr-2" />
            GPCI Localities
          </TabsTrigger>
        </TabsList>

        {/* Search Tab */}
        <TabsContent value="search" className="mt-6">
          <div className="container-card">
            <div className="flex gap-4 mb-6">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
                <Input
                  placeholder="Search by CPT code or description (e.g., 99213, office visit)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10 input-field"
                  data-testid="cpt-search-input"
                />
              </div>
              <Select value={selectedLocality} onValueChange={handleLocalityChange}>
                <SelectTrigger className="w-64" data-testid="locality-select">
                  <MapPin className="h-4 w-4 mr-2 text-[#8A8A85]" />
                  <SelectValue placeholder="Select Locality" />
                </SelectTrigger>
                <SelectContent className="max-h-80">
                  {localities.map((loc) => (
                    <SelectItem key={loc.code} value={loc.code}>
                      {loc.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button 
                onClick={handleSearch} 
                className="btn-primary"
                disabled={searchLoading}
                data-testid="search-cpt-btn"
              >
                {searchLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </>
                )}
              </Button>
            </div>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="border border-[#E2E2DF] rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="table-header">
                      <TableHead className="w-[100px]">CPT Code</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Work RVU</TableHead>
                      <TableHead className="text-right">Total RVU</TableHead>
                      <TableHead className="text-right">National Rate</TableHead>
                      <TableHead className="w-[80px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {searchResults.map((code) => (
                      <TableRow 
                        key={code.code} 
                        className="table-row hover:bg-[#F7F7F4] cursor-pointer transition-colors"
                        onClick={() => handleCodeClick(code)}
                        data-testid={`cpt-row-${code.code}`}
                      >
                        <TableCell className="font-['JetBrains_Mono'] text-xs font-medium">
                          {code.code}
                        </TableCell>
                        <TableCell className="max-w-[300px] truncate text-sm">
                          {code.description}
                        </TableCell>
                        <TableCell>
                          <Badge className={`${CATEGORY_COLORS[code.category] || 'bg-[#64645F] text-white'} text-xs`}>
                            {code.category}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                          {code.work_rvu?.toFixed(2) || '-'}
                        </TableCell>
                        <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                          {code.total_rvu?.toFixed(2) || '-'}
                        </TableCell>
                        <TableCell className="text-right font-['JetBrains_Mono'] text-xs text-[#4B6E4E]">
                          {formatCurrency(code.facility_rate)}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            <Calculator className="h-4 w-4 text-[#64645F]" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {searchResults.length === 0 && searchQuery && !searchLoading && (
              <div className="text-center py-12">
                <Search className="h-12 w-12 text-[#E2E2DF] mx-auto mb-4" />
                <p className="text-[#64645F]">No results found for "{searchQuery}"</p>
                <p className="text-sm text-[#8A8A85] mt-1">
                  Try a different search term or CPT code
                </p>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Localities Tab */}
        <TabsContent value="localities" className="mt-6">
          <div className="container-card p-0 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="table-header">
                  <TableHead>Locality Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Work GPCI</TableHead>
                  <TableHead className="text-right">PE GPCI</TableHead>
                  <TableHead className="text-right">MP GPCI</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {localities.map((loc) => (
                  <TableRow 
                    key={loc.code} 
                    className="table-row hover:bg-[#F7F7F4] transition-colors"
                    data-testid={`locality-row-${loc.code}`}
                  >
                    <TableCell className="font-['JetBrains_Mono'] text-xs">
                      {loc.code}
                    </TableCell>
                    <TableCell className="font-medium">{loc.name}</TableCell>
                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                      <span className={loc.work_gpci > 1 ? 'text-[#C24A3B]' : loc.work_gpci < 1 ? 'text-[#4B6E4E]' : ''}>
                        {loc.work_gpci.toFixed(3)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                      <span className={loc.pe_gpci > 1 ? 'text-[#C24A3B]' : loc.pe_gpci < 1 ? 'text-[#4B6E4E]' : ''}>
                        {loc.pe_gpci.toFixed(3)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-['JetBrains_Mono'] text-xs">
                      <span className={loc.mp_gpci > 1 ? 'text-[#C24A3B]' : loc.mp_gpci < 1 ? 'text-[#4B6E4E]' : ''}>
                        {loc.mp_gpci.toFixed(3)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* Code Detail Modal */}
      <Dialog open={showCodeDetail} onOpenChange={setShowCodeDetail}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-['Outfit'] flex items-center gap-3">
              <span className="font-['JetBrains_Mono'] text-lg">{selectedCode?.code}</span>
              {selectedCode?.category && (
                <Badge className={`${CATEGORY_COLORS[selectedCode.category] || 'bg-[#64645F] text-white'}`}>
                  {selectedCode.category}
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription className="text-left">
              {selectedCode?.description}
            </DialogDescription>
          </DialogHeader>

          {rateDetails && (
            <div className="space-y-6 py-4">
              {/* Locality Selection */}
              <div className="flex items-center gap-4">
                <Label className="text-sm font-medium">Calculate for Locality:</Label>
                <Select value={selectedLocality} onValueChange={handleLocalityChange}>
                  <SelectTrigger className="w-64">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-80">
                    {localities.map((loc) => (
                      <SelectItem key={loc.code} value={loc.code}>
                        {loc.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* RVU Breakdown */}
              <div className="bg-[#F7F7F4] rounded-lg p-4">
                <h4 className="text-sm font-medium text-[#1C1C1A] mb-3">
                  Relative Value Units (RVUs)
                </h4>
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-xs text-[#64645F]">Work</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono']">
                      {rateDetails.work_rvu?.toFixed(2) || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[#64645F]">Practice Expense</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono']">
                      {rateDetails.pe_rvu?.toFixed(2) || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[#64645F]">Malpractice</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono']">
                      {rateDetails.mp_rvu?.toFixed(2) || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[#64645F]">Total</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono'] text-[#1A3636]">
                      {rateDetails.total_rvu?.toFixed(2) || '-'}
                    </p>
                  </div>
                </div>
              </div>

              {/* GPCI Factors */}
              <div className="bg-[#EEF3F9] rounded-lg p-4">
                <h4 className="text-sm font-medium text-[#1C1C1A] mb-3 flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  GPCI Factors - {rateDetails.locality_name}
                </h4>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-xs text-[#64645F]">Work GPCI</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono']">
                      {rateDetails.gpci_work?.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[#64645F]">PE GPCI</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono']">
                      {rateDetails.gpci_pe?.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[#64645F]">MP GPCI</p>
                    <p className="text-lg font-semibold font-['JetBrains_Mono']">
                      {rateDetails.gpci_mp?.toFixed(3)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Calculated Rate */}
              <div className="bg-[#EDF2EE] rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-[#64645F]">
                      GPCI-Adjusted Medicare Rate
                    </h4>
                    <p className="text-xs text-[#8A8A85] mt-1">
                      Conversion Factor: ${rateDetails.conversion_factor}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-[#4B6E4E] font-['Outfit']">
                      {formatCurrency(rateDetails.medicare_rate)}
                    </p>
                    <p className="text-xs text-[#64645F] mt-1">
                      National: {formatCurrency(rateDetails.national_facility_rate)} (Facility)
                    </p>
                  </div>
                </div>
              </div>

              {/* Formula */}
              <div className="border border-[#E2E2DF] rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 text-[#64645F] mt-0.5" />
                  <div className="text-xs text-[#64645F]">
                    <p className="font-medium mb-1">Medicare Payment Formula:</p>
                    <p className="font-['JetBrains_Mono']">
                      [(Work RVU × Work GPCI) + (PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × Conversion Factor
                    </p>
                    <p className="mt-2 font-['JetBrains_Mono']">
                      [({rateDetails.work_rvu} × {rateDetails.gpci_work}) + ({rateDetails.pe_rvu} × {rateDetails.gpci_pe}) + ({rateDetails.mp_rvu} × {rateDetails.gpci_mp})] × ${rateDetails.conversion_factor}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
