import { useState, useEffect } from 'react';
import { tieringAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Gauge, RefreshCw, Zap, Shield, AlertTriangle, Search, ArrowRight,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';

export default function DataTiering() {
  const [summary, setSummary] = useState(null);
  const [riskDial, setRiskDial] = useState(null);
  const [loading, setLoading] = useState(true);
  const [classifying, setClassifying] = useState(false);
  const [claimSearch, setClaimSearch] = useState('');
  const [claimTier, setClaimTier] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sumRes, riskRes] = await Promise.all([
        tieringAPI.summary(),
        tieringAPI.riskDial(),
      ]);
      setSummary(sumRes.data);
      setRiskDial(riskRes.data);
    } catch { toast.error('Failed to load tiering data'); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleBatchClassify = async () => {
    setClassifying(true);
    try {
      const res = await tieringAPI.batchClassify(500);
      toast.success(`Classified ${res.data.processed} claims`);
      fetchData();
    } catch { toast.error('Batch classify failed'); }
    finally { setClassifying(false); }
  };

  const searchClaim = async () => {
    if (!claimSearch.trim()) return;
    try {
      const res = await tieringAPI.analyzeClaim(claimSearch.trim());
      setClaimTier(res.data);
    } catch { toast.error('Claim not found'); setClaimTier(null); }
  };

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0);

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>;

  return (
    <div className="space-y-6" data-testid="data-tiering-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">Data Tiering Engine</h1>
          <p className="text-sm text-[#64645F]">Classify claims into Auto-Pilot, Clinical Review, and Stop-Loss tiers</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={fetchData} className="text-xs" data-testid="refresh-tiering"><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
          <Button onClick={handleBatchClassify} disabled={classifying} className="btn-primary text-xs" data-testid="batch-classify-btn">
            {classifying ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Zap className="h-3.5 w-3.5 mr-1" />}
            Batch Classify
          </Button>
        </div>
      </div>

      {/* Tier Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="tier-summary">
          <div className="container-card bg-[#F0F7F1] border border-[#D4E5D6]" data-testid="tier-1-card">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-9 h-9 bg-[#4B6E4E] rounded-lg flex items-center justify-center"><Zap className="h-4 w-4 text-white" /></div>
              <div>
                <p className="text-sm font-medium text-[#4B6E4E]">Tier 1 — Auto-Pilot</p>
                <p className="text-[10px] text-[#8A8A85]">{summary.tier_1.description}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><p className="text-[10px] text-[#64645F]">Claims</p><p className="text-xl font-semibold font-['Outfit'] text-[#1C1C1A]">{summary.tier_1.count}</p></div>
              <div><p className="text-[10px] text-[#64645F]">Paid</p><p className="text-xl font-semibold font-['JetBrains_Mono'] text-[#4B6E4E]">{fmt(summary.tier_1.total_paid)}</p></div>
            </div>
          </div>
          <div className="container-card bg-[#FDF3E1] border border-[#F5D88E]" data-testid="tier-2-card">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-9 h-9 bg-[#C9862B] rounded-lg flex items-center justify-center"><Search className="h-4 w-4 text-white" /></div>
              <div>
                <p className="text-sm font-medium text-[#C9862B]">Tier 2 — Clinical Review</p>
                <p className="text-[10px] text-[#8A8A85]">{summary.tier_2.description}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><p className="text-[10px] text-[#64645F]">Claims</p><p className="text-xl font-semibold font-['Outfit'] text-[#1C1C1A]">{summary.tier_2.count}</p></div>
              <div><p className="text-[10px] text-[#64645F]">Paid</p><p className="text-xl font-semibold font-['JetBrains_Mono'] text-[#C9862B]">{fmt(summary.tier_2.total_paid)}</p></div>
            </div>
          </div>
          <div className="container-card bg-[#FBEAE7] border border-[#E8C4BE]" data-testid="tier-3-card">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-9 h-9 bg-[#C24A3B] rounded-lg flex items-center justify-center"><AlertTriangle className="h-4 w-4 text-white" /></div>
              <div>
                <p className="text-sm font-medium text-[#C24A3B]">Tier 3 — Stop-Loss Trigger</p>
                <p className="text-[10px] text-[#8A8A85]">{summary.tier_3.description}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><p className="text-[10px] text-[#64645F]">Claims</p><p className="text-xl font-semibold font-['Outfit'] text-[#1C1C1A]">{summary.tier_3.count}</p></div>
              <div><p className="text-[10px] text-[#64645F]">Paid</p><p className="text-xl font-semibold font-['JetBrains_Mono'] text-[#C24A3B]">{fmt(summary.tier_3.total_paid)}</p></div>
            </div>
          </div>
        </div>
      )}

      {/* Claim Tier Lookup */}
      <div className="container-card" data-testid="claim-tier-lookup">
        <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-3">Claim Tier Lookup</h3>
        <div className="flex gap-2 mb-4">
          <Input value={claimSearch} onChange={e => setClaimSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchClaim()}
            placeholder="Enter Claim ID to analyze..." className="input-field" data-testid="claim-search-input" />
          <Button onClick={searchClaim} className="btn-primary" data-testid="analyze-claim-btn"><Search className="h-4 w-4 mr-1" />Analyze</Button>
        </div>
        {claimTier && (
          <div className={`rounded-xl p-4 border ${claimTier.tier === 1 ? 'bg-[#F0F7F1] border-[#D4E5D6]' : claimTier.tier === 2 ? 'bg-[#FDF3E1] border-[#F5D88E]' : 'bg-[#FBEAE7] border-[#E8C4BE]'}`} data-testid="claim-tier-result">
            <div className="flex items-center gap-3 mb-2">
              <Badge className={`border-0 text-xs text-white ${claimTier.tier === 1 ? 'bg-[#4B6E4E]' : claimTier.tier === 2 ? 'bg-[#C9862B]' : 'bg-[#C24A3B]'}`}>
                TIER {claimTier.tier} — {claimTier.tier_label}
              </Badge>
              <span className="text-xs text-[#64645F]">Claim: {claimTier.claim_id}</span>
            </div>
            <p className="text-sm text-[#1C1C1A]">{claimTier.tier_reason}</p>
            <div className="flex gap-4 mt-2 text-xs text-[#64645F]">
              <span>Paid: <strong className="font-['JetBrains_Mono']">{fmt(claimTier.total_paid)}</strong></span>
              <span>Billed: <strong className="font-['JetBrains_Mono']">{fmt(claimTier.total_billed)}</strong></span>
              {claimTier.has_trigger_codes && <Badge className="bg-[#C9862B] text-white border-0 text-[9px]">Trigger CPT</Badge>}
              {claimTier.has_prior_auth && <Badge className="bg-[#5C2D91] text-white border-0 text-[9px]">Prior Auth</Badge>}
            </div>
          </div>
        )}
      </div>

      {/* Risk Dial */}
      {riskDial && riskDial.groups.length > 0 && (
        <div className="container-card" data-testid="risk-dial-section">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#FBEAE7] rounded-lg flex items-center justify-center"><Gauge className="h-5 w-5 text-[#C24A3B]" /></div>
              <div>
                <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Stop-Loss Risk Monitor</h3>
                <p className="text-[10px] text-[#8A8A85]">Agg/Spec utilization tracked in real-time</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {riskDial.summary.critical > 0 && <Badge className="bg-[#C24A3B] text-white border-0 text-[10px] animate-pulse">{riskDial.summary.critical} CRITICAL</Badge>}
              {riskDial.summary.warning > 0 && <Badge className="bg-[#C9862B] text-white border-0 text-[10px]">{riskDial.summary.warning} WARNING</Badge>}
            </div>
          </div>
          <div className="space-y-3">
            {riskDial.groups.map(g => {
              const barColor = g.alert_level === 'critical' ? 'bg-[#C24A3B]' : g.alert_level === 'warning' ? 'bg-[#C9862B]' : 'bg-[#4B6E4E]';
              const bgColor = g.alert_level === 'critical' ? 'bg-[#FBEAE7]' : g.alert_level === 'warning' ? 'bg-[#FDF3E1]' : 'bg-[#F7F7F4]';
              return (
                <div key={g.group_id} className={`${bgColor} rounded-xl p-4 border border-[#E2E2DF]`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-[#1C1C1A]">{g.group_name}</p>
                      <span className="text-[10px] text-[#8A8A85]">{g.plan_name}</span>
                      {g.stop_loss_carrier && <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-[9px]">{g.stop_loss_carrier}</Badge>}
                    </div>
                    <Badge className={`border-0 text-[10px] text-white ${barColor}`}>{g.alert_level.toUpperCase()}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="flex justify-between text-[10px] text-[#64645F] mb-1">
                        <span>Specific ({fmt(g.highest_member_claims)} / {fmt(g.specific_attachment_point)})</span>
                        <span className="font-['JetBrains_Mono'] font-semibold">{g.specific_utilization_pct}%</span>
                      </div>
                      <div className="w-full bg-[#E2E2DF] rounded-full h-2.5">
                        <div className={`${barColor} h-2.5 rounded-full transition-all`} style={{ width: `${Math.min(g.specific_utilization_pct, 100)}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-[#64645F] mb-1">
                        <span>Aggregate ({fmt(g.group_total_claims)} / {fmt(g.aggregate_attachment_point)})</span>
                        <span className="font-['JetBrains_Mono'] font-semibold">{g.aggregate_utilization_pct}%</span>
                      </div>
                      <div className="w-full bg-[#E2E2DF] rounded-full h-2.5">
                        <div className={`${barColor} h-2.5 rounded-full transition-all`} style={{ width: `${Math.min(g.aggregate_utilization_pct, 100)}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
