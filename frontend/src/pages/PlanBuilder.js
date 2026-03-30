import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { plansAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  ArrowLeft, Plus, Trash2, Save, RefreshCw, Shield, Heart, Building2,
  Syringe, AlertTriangle, FileDown, Stethoscope, Layers, DollarSign,
  Activity, Zap, ChevronDown, ChevronUp,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const DEFAULT_MODULES = [
  { module_id: 'preventive', enabled: true, copay: 0, deductible: 0, coinsurance: 0, deductible_applies: false, prior_auth_required: false, visit_limit: null, notes: 'ACA-mandated preventive services at $0 cost share' },
  { module_id: 'physician', enabled: true, copay: 30, deductible: 0, coinsurance: 20, deductible_applies: true, prior_auth_required: false, visit_limit: null, notes: '' },
  { module_id: 'inpatient', enabled: true, copay: 500, deductible: 0, coinsurance: 20, deductible_applies: true, prior_auth_required: true, visit_limit: null, notes: '' },
  { module_id: 'emergency', enabled: true, copay: 250, deductible: 0, coinsurance: 20, deductible_applies: true, prior_auth_required: false, visit_limit: null, notes: '' },
  { module_id: 'pharmacy', enabled: true, copay: 10, deductible: 0, coinsurance: 25, deductible_applies: false, prior_auth_required: false, visit_limit: null, notes: 'Tier 1 Generic / Tier 2 Brand / Tier 3 Specialty' },
];

const DEFAULT_TIERS = [
  { tier_id: 'tier1', name: 'Tier 1 — Narrow Network', copay_modifier: 1.0, coinsurance: 20, deductible: 500, oop_max: 5000, description: 'Primary contracted providers' },
  { tier_id: 'tier2', name: 'Tier 2 — Wrap Network', copay_modifier: 1.5, coinsurance: 40, deductible: 1000, oop_max: 8000, description: 'Extended network providers' },
];

const DEFAULT_RISK = { specific_attachment_point: 250000, aggregate_attachment_point: 1000000, auto_flag_threshold_pct: 50, stop_loss_carrier: '', contract_period: '12_month', notes: '' };

const MODULE_META = {
  preventive: { label: 'Preventive Care (ACA)', icon: Heart, color: 'bg-[#4B6E4E]', desc: 'Annual physicals, immunizations, screenings — mandated at $0 cost share under ACA' },
  physician: { label: 'Physician / Office Visit', icon: Stethoscope, color: 'bg-[#4A6FA5]', desc: 'Primary care, specialist visits, telehealth consultations' },
  inpatient: { label: 'Inpatient / Hospital', icon: Building2, color: 'bg-[#5C2D91]', desc: 'Hospital admissions, surgical procedures, room & board' },
  emergency: { label: 'Emergency / Urgent Care', icon: Zap, color: 'bg-[#C24A3B]', desc: 'ER visits, urgent care centers, ambulance services' },
  pharmacy: { label: 'Pharmacy (Rx)', icon: Syringe, color: 'bg-[#C9862B]', desc: 'Generic, brand, specialty drugs — tiered formulary' },
};

const defaultBenefit = { service_category: '', covered: true, copay: 0, coinsurance: 0.2, deductible_applies: true, annual_max: null, visit_limit: null, frequency_limit: '', waiting_period_days: 0, prior_auth_required: false, code_range: '' };

const SERVICE_CATEGORIES = ['Preventive Care', 'Office Visit', 'Emergency Room', 'Urgent Care', 'Hospital Inpatient', 'Hospital Outpatient', 'Surgery', 'Lab & Diagnostics', 'Imaging', 'Physical Therapy', 'Mental Health', 'Prescription Drugs', 'Durable Medical Equipment', 'Specialist Visit', 'Maternity', 'Other'];

export default function PlanBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  const [formData, setFormData] = useState({
    name: '', plan_type: 'medical', group_id: '',
    effective_date: new Date().toISOString().split('T')[0], termination_date: '',
    deductible_individual: 500, deductible_family: 1500,
    oop_max_individual: 5000, oop_max_family: 10000,
    network_type: 'PPO', reimbursement_method: 'fee_schedule', rbp_medicare_pct: 150,
    tier_type: 'employee_only', benefits: [], benefit_modules: [...DEFAULT_MODULES],
    network_tiers: [...DEFAULT_TIERS],
    risk_management: { ...DEFAULT_RISK },
    exclusions: [], preventive_design: 'aca_strict',
  });

  const [exclusionInput, setExclusionInput] = useState('');
  const [expandedModule, setExpandedModule] = useState(null);

  useEffect(() => { if (isEdit) fetchPlan(); }, [id]);

  const fetchPlan = async () => {
    try {
      const response = await plansAPI.get(id);
      const data = response.data;
      // Ensure new fields have defaults if missing
      if (!data.benefit_modules?.length) data.benefit_modules = [...DEFAULT_MODULES];
      if (!data.network_tiers?.length) data.network_tiers = [...DEFAULT_TIERS];
      if (!data.risk_management) data.risk_management = { ...DEFAULT_RISK };
      if (!data.rbp_medicare_pct) data.rbp_medicare_pct = 150;
      setFormData(data);
    } catch { toast.error('Failed to load plan'); navigate('/plans'); }
    finally { setLoading(false); }
  };

  const handleChange = (field, value) => setFormData((prev) => ({ ...prev, [field]: value }));

  // Module handlers
  const updateModule = (moduleId, field, value) => {
    setFormData(prev => ({
      ...prev,
      benefit_modules: prev.benefit_modules.map(m =>
        m.module_id === moduleId ? { ...m, [field]: value } : m
      ),
    }));
  };

  // Tier handlers
  const updateTier = (tierIdx, field, value) => {
    setFormData(prev => ({
      ...prev,
      network_tiers: prev.network_tiers.map((t, i) => i === tierIdx ? { ...t, [field]: value } : t),
    }));
  };
  const addTier = () => {
    const num = formData.network_tiers.length + 1;
    setFormData(prev => ({
      ...prev,
      network_tiers: [...prev.network_tiers, { tier_id: `tier${num}`, name: `Tier ${num}`, copay_modifier: 1.0, coinsurance: 30, deductible: 0, oop_max: 0, description: '' }],
    }));
  };
  const removeTier = (idx) => setFormData(prev => ({ ...prev, network_tiers: prev.network_tiers.filter((_, i) => i !== idx) }));

  // Risk handler
  const updateRisk = (field, value) => setFormData(prev => ({ ...prev, risk_management: { ...prev.risk_management, [field]: value } }));

  // Legacy benefit handlers
  const handleBenefitChange = (index, field, value) => {
    const n = [...formData.benefits]; n[index] = { ...n[index], [field]: value };
    setFormData(prev => ({ ...prev, benefits: n }));
  };
  const addBenefit = () => setFormData(prev => ({ ...prev, benefits: [...prev.benefits, { ...defaultBenefit }] }));
  const removeBenefit = (index) => setFormData(prev => ({ ...prev, benefits: prev.benefits.filter((_, i) => i !== index) }));

  const addExclusion = () => { if (exclusionInput.trim()) { setFormData(prev => ({ ...prev, exclusions: [...prev.exclusions, exclusionInput.trim()] })); setExclusionInput(''); } };
  const removeExclusion = (index) => setFormData(prev => ({ ...prev, exclusions: prev.exclusions.filter((_, i) => i !== index) }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (isEdit) { await plansAPI.update(id, formData); toast.success('Plan updated'); }
      else { await plansAPI.create(formData); toast.success('Plan created'); }
      navigate('/plans');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to save plan'); }
    finally { setSaving(false); }
  };

  const downloadSBC = () => {
    if (!isEdit) { toast.error('Save the plan first to generate SBC'); return; }
    const token = localStorage.getItem('token');
    window.open(plansAPI.sbcPdfUrl(id) + `?token=${token}`, '_blank');
  };

  const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v || 0);

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-6 w-6 animate-spin text-[#1A3636]" /></div>;

  return (
    <div className="space-y-6" data-testid="plan-builder">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/plans')} className="p-2" data-testid="back-btn"><ArrowLeft className="h-5 w-5" /></Button>
          <div>
            <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">{isEdit ? 'Edit Plan' : 'Create Plan'}</h1>
            <p className="text-sm text-[#64645F]">{isEdit ? formData.name : 'Configure benefit design, network tiers, and risk management'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isEdit && (
            <Button variant="outline" onClick={downloadSBC} className="text-xs" data-testid="sbc-download-btn">
              <FileDown className="h-3.5 w-3.5 mr-1.5" />Generate SBC
            </Button>
          )}
          <Button onClick={handleSubmit} disabled={saving} className="btn-primary" data-testid="save-plan-btn">
            {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            {isEdit ? 'Update Plan' : 'Create Plan'}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="bg-[#F0F0EA] p-1 rounded-xl">
            <TabsTrigger value="general" className="data-[state=active]:bg-white text-sm" data-testid="tab-general"><Shield className="h-3.5 w-3.5 mr-1.5" />General</TabsTrigger>
            <TabsTrigger value="cost" className="data-[state=active]:bg-white text-sm" data-testid="tab-cost"><DollarSign className="h-3.5 w-3.5 mr-1.5" />Cost Sharing</TabsTrigger>
            <TabsTrigger value="benefits" className="data-[state=active]:bg-white text-sm" data-testid="tab-benefits"><Layers className="h-3.5 w-3.5 mr-1.5" />Benefit Modules</TabsTrigger>
            <TabsTrigger value="network" className="data-[state=active]:bg-white text-sm" data-testid="tab-network"><Activity className="h-3.5 w-3.5 mr-1.5" />Network Tiers</TabsTrigger>
            <TabsTrigger value="risk" className="data-[state=active]:bg-white text-sm" data-testid="tab-risk"><AlertTriangle className="h-3.5 w-3.5 mr-1.5" />Risk Management</TabsTrigger>
            <TabsTrigger value="exclusions" className="data-[state=active]:bg-white text-sm" data-testid="tab-exclusions">Exclusions</TabsTrigger>
          </TabsList>

          {/* ═══ GENERAL TAB ═══ */}
          <TabsContent value="general" className="mt-6 space-y-6">
            <div className="container-card">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Plan Information</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Plan Name *</Label><Input value={formData.name} onChange={(e) => handleChange('name', e.target.value)} className="input-field" required data-testid="plan-name" /></div>
                <div className="space-y-2"><Label>Plan Type</Label>
                  <Select value={formData.plan_type} onValueChange={(v) => handleChange('plan_type', v)}>
                    <SelectTrigger className="input-field" data-testid="plan-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="medical">Medical</SelectItem>
                      <SelectItem value="dental">Dental</SelectItem>
                      <SelectItem value="vision">Vision</SelectItem>
                      <SelectItem value="pharmacy">Pharmacy</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2"><Label>Group ID</Label><Input value={formData.group_id} onChange={(e) => handleChange('group_id', e.target.value)} className="input-field" data-testid="plan-group-id" /></div>
                <div className="space-y-2"><Label>Network Type</Label>
                  <Select value={formData.network_type} onValueChange={(v) => handleChange('network_type', v)}>
                    <SelectTrigger className="input-field" data-testid="plan-network-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PPO">PPO</SelectItem>
                      <SelectItem value="HMO">HMO</SelectItem>
                      <SelectItem value="EPO">EPO</SelectItem>
                      <SelectItem value="POS">POS</SelectItem>
                      <SelectItem value="HDHP">HDHP</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2"><Label>Effective Date</Label><Input type="date" value={formData.effective_date} onChange={(e) => handleChange('effective_date', e.target.value)} className="input-field" data-testid="plan-eff-date" /></div>
                <div className="space-y-2"><Label>Termination Date</Label><Input type="date" value={formData.termination_date || ''} onChange={(e) => handleChange('termination_date', e.target.value)} className="input-field" /></div>
                <div className="space-y-2"><Label>Reimbursement Method</Label>
                  <Select value={formData.reimbursement_method} onValueChange={(v) => handleChange('reimbursement_method', v)}>
                    <SelectTrigger className="input-field" data-testid="plan-reimb-method"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fee_schedule">Fee Schedule</SelectItem>
                      <SelectItem value="percent_medicare">% of Medicare</SelectItem>
                      <SelectItem value="rbp">Reference Based Pricing (RBP)</SelectItem>
                      <SelectItem value="contracted">Contracted Network</SelectItem>
                      <SelectItem value="percent_billed">% of Billed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {formData.reimbursement_method === 'rbp' && (
                  <div className="space-y-2">
                    <Label>RBP — % of Medicare</Label>
                    <Input type="number" value={formData.rbp_medicare_pct} onChange={(e) => handleChange('rbp_medicare_pct', parseFloat(e.target.value) || 150)} className="input-field" data-testid="plan-rbp-pct" />
                    <p className="text-[10px] text-[#8A8A85]">Claims auto-adjudicate at this % of the Medicare Fee Schedule</p>
                  </div>
                )}
                <div className="space-y-2"><Label>Preventive Design</Label>
                  <Select value={formData.preventive_design} onValueChange={(v) => handleChange('preventive_design', v)}>
                    <SelectTrigger className="input-field" data-testid="plan-prev-design"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="aca_strict">ACA Strict</SelectItem>
                      <SelectItem value="aca_plus">ACA Plus (Enhanced)</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2"><Label>Tier Type</Label>
                  <Select value={formData.tier_type} onValueChange={(v) => handleChange('tier_type', v)}>
                    <SelectTrigger className="input-field" data-testid="plan-tier-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="employee_only">Employee Only</SelectItem>
                      <SelectItem value="employee_spouse">Employee + Spouse</SelectItem>
                      <SelectItem value="employee_children">Employee + Children</SelectItem>
                      <SelectItem value="family">Family</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* ═══ COST SHARING TAB ═══ */}
          <TabsContent value="cost" className="mt-6 space-y-6">
            <div className="container-card">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Deductibles & Out-of-Pocket Maximums</h2>
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-[#F7F7F4] rounded-xl p-5 border border-[#E2E2DF]">
                  <p className="text-sm font-medium text-[#1C1C1A] mb-3">Individual</p>
                  <div className="space-y-3">
                    <div className="space-y-1"><Label className="text-[10px]">Annual Deductible</Label><Input type="number" value={formData.deductible_individual} onChange={(e) => handleChange('deductible_individual', parseFloat(e.target.value) || 0)} className="input-field" data-testid="ded-individual" /></div>
                    <div className="space-y-1"><Label className="text-[10px]">Out-of-Pocket Maximum</Label><Input type="number" value={formData.oop_max_individual} onChange={(e) => handleChange('oop_max_individual', parseFloat(e.target.value) || 0)} className="input-field" data-testid="oop-individual" /></div>
                  </div>
                </div>
                <div className="bg-[#F7F7F4] rounded-xl p-5 border border-[#E2E2DF]">
                  <p className="text-sm font-medium text-[#1C1C1A] mb-3">Family</p>
                  <div className="space-y-3">
                    <div className="space-y-1"><Label className="text-[10px]">Annual Deductible</Label><Input type="number" value={formData.deductible_family} onChange={(e) => handleChange('deductible_family', parseFloat(e.target.value) || 0)} className="input-field" data-testid="ded-family" /></div>
                    <div className="space-y-1"><Label className="text-[10px]">Out-of-Pocket Maximum</Label><Input type="number" value={formData.oop_max_family} onChange={(e) => handleChange('oop_max_family', parseFloat(e.target.value) || 0)} className="input-field" data-testid="oop-family" /></div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* ═══ BENEFIT MODULES TAB ═══ */}
          <TabsContent value="benefits" className="mt-6 space-y-4">
            <div className="container-card">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Benefit Stacking</h2>
                  <p className="text-xs text-[#8A8A85] mt-1">Toggle and configure each benefit module independently. Disabled modules are excluded from adjudication.</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className="bg-[#F0F0EA] text-[#64645F] border-0 text-xs">{formData.benefit_modules.filter(m => m.enabled).length} / {formData.benefit_modules.length} active</Badge>
                </div>
              </div>

              <div className="space-y-3" data-testid="benefit-modules-list">
                {formData.benefit_modules.map((mod) => {
                  const meta = MODULE_META[mod.module_id] || {};
                  const Icon = meta.icon || Shield;
                  const isExpanded = expandedModule === mod.module_id;
                  return (
                    <div key={mod.module_id}
                      className={`rounded-xl border transition-all ${mod.enabled ? 'bg-white border-[#E2E2DF]' : 'bg-[#F7F7F4] border-[#E2E2DF] opacity-60'}`}
                      data-testid={`module-${mod.module_id}`}
                    >
                      <div className="flex items-center justify-between p-4 cursor-pointer" onClick={() => setExpandedModule(isExpanded ? null : mod.module_id)}>
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 ${meta.color} rounded-lg flex items-center justify-center`}><Icon className="h-4.5 w-4.5 text-white" /></div>
                          <div>
                            <p className="text-sm font-medium text-[#1C1C1A]">{meta.label}</p>
                            <p className="text-[10px] text-[#8A8A85]">{meta.desc}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {mod.enabled && (
                            <div className="flex items-center gap-3 text-xs text-[#64645F]">
                              <span>Copay: <strong className="font-['JetBrains_Mono']">{fmt(mod.copay)}</strong></span>
                              <span>Coins: <strong className="font-['JetBrains_Mono']">{mod.coinsurance}%</strong></span>
                              {mod.prior_auth_required && <Badge className="bg-[#C9862B] text-white border-0 text-[9px]">Prior Auth</Badge>}
                            </div>
                          )}
                          <Switch checked={mod.enabled} onCheckedChange={(v) => updateModule(mod.module_id, 'enabled', v)} onClick={(e) => e.stopPropagation()} data-testid={`toggle-${mod.module_id}`} />
                          {isExpanded ? <ChevronUp className="h-4 w-4 text-[#8A8A85]" /> : <ChevronDown className="h-4 w-4 text-[#8A8A85]" />}
                        </div>
                      </div>

                      {isExpanded && mod.enabled && (
                        <div className="px-4 pb-4 border-t border-[#E2E2DF] pt-3">
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                            <div className="space-y-1">
                              <Label className="text-[10px]">Copay ($)</Label>
                              <Input type="number" value={mod.copay} onChange={(e) => updateModule(mod.module_id, 'copay', parseFloat(e.target.value) || 0)} className="input-field h-8 text-xs" data-testid={`copay-${mod.module_id}`} />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-[10px]">Deductible ($)</Label>
                              <Input type="number" value={mod.deductible} onChange={(e) => updateModule(mod.module_id, 'deductible', parseFloat(e.target.value) || 0)} className="input-field h-8 text-xs" data-testid={`deductible-${mod.module_id}`} />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-[10px]">Coinsurance (%)</Label>
                              <Input type="number" value={mod.coinsurance} onChange={(e) => updateModule(mod.module_id, 'coinsurance', parseFloat(e.target.value) || 0)} className="input-field h-8 text-xs" data-testid={`coinsurance-${mod.module_id}`} />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-[10px]">Visit Limit</Label>
                              <Input type="number" value={mod.visit_limit || ''} onChange={(e) => updateModule(mod.module_id, 'visit_limit', e.target.value ? parseInt(e.target.value) : null)} className="input-field h-8 text-xs" placeholder="Unlimited" />
                            </div>
                            <div className="flex flex-col gap-2 justify-end">
                              <div className="flex items-center gap-2">
                                <Switch checked={mod.deductible_applies} onCheckedChange={(v) => updateModule(mod.module_id, 'deductible_applies', v)} />
                                <Label className="text-[10px]">Deductible Applies</Label>
                              </div>
                              <div className="flex items-center gap-2">
                                <Switch checked={mod.prior_auth_required} onCheckedChange={(v) => updateModule(mod.module_id, 'prior_auth_required', v)} data-testid={`auth-${mod.module_id}`} />
                                <Label className="text-[10px]">Prior Auth Required</Label>
                              </div>
                            </div>
                          </div>
                          <div className="mt-3">
                            <Label className="text-[10px]">Notes</Label>
                            <Input value={mod.notes} onChange={(e) => updateModule(mod.module_id, 'notes', e.target.value)} className="input-field h-8 text-xs mt-1" placeholder="Additional configuration notes..." />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Legacy Benefits (advanced) */}
            <div className="container-card">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-medium text-[#1C1C1A] font-['Outfit']">Additional Service-Level Benefits</h3>
                  <p className="text-[10px] text-[#8A8A85]">Fine-grained overrides for specific service categories beyond the module defaults</p>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={addBenefit} className="text-xs" data-testid="add-benefit-btn"><Plus className="h-3 w-3 mr-1" />Add Benefit</Button>
              </div>
              {formData.benefits.length === 0 ? (
                <div className="bg-[#F7F7F4] rounded-lg p-4 text-center text-xs text-[#8A8A85]">No additional benefits. Module defaults apply.</div>
              ) : (
                <div className="space-y-2">
                  {formData.benefits.map((b, i) => (
                    <div key={i} className="bg-[#F7F7F4] rounded-lg p-3 border border-[#E2E2DF] flex items-center gap-3">
                      <Select value={b.service_category} onValueChange={(v) => handleBenefitChange(i, 'service_category', v)}>
                        <SelectTrigger className="input-field h-7 text-xs w-[160px]"><SelectValue placeholder="Category" /></SelectTrigger>
                        <SelectContent>{SERVICE_CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                      </Select>
                      <Input type="number" value={b.copay} onChange={(e) => handleBenefitChange(i, 'copay', parseFloat(e.target.value) || 0)} className="input-field h-7 text-xs w-20" placeholder="Copay" />
                      <Input type="number" value={b.coinsurance} onChange={(e) => handleBenefitChange(i, 'coinsurance', parseFloat(e.target.value) || 0)} className="input-field h-7 text-xs w-20" placeholder="Coins" />
                      <Switch checked={b.prior_auth_required} onCheckedChange={(v) => handleBenefitChange(i, 'prior_auth_required', v)} />
                      <span className="text-[9px] text-[#8A8A85]">Auth</span>
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeBenefit(i)} className="h-7 w-7 p-0 text-[#C24A3B] ml-auto"><Trash2 className="h-3.5 w-3.5" /></Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* ═══ NETWORK TIERS TAB ═══ */}
          <TabsContent value="network" className="mt-6 space-y-4">
            <div className="container-card">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Network Tiers</h2>
                  <p className="text-xs text-[#8A8A85] mt-1">Configure different cost-sharing levels based on network tier (Narrow, Wrap, Out-of-Network).</p>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={addTier} className="text-xs" data-testid="add-tier-btn"><Plus className="h-3 w-3 mr-1" />Add Tier</Button>
              </div>
              <div className="space-y-3" data-testid="network-tiers-list">
                {formData.network_tiers.map((tier, idx) => (
                  <div key={tier.tier_id} className="bg-[#F7F7F4] rounded-xl p-5 border border-[#E2E2DF]" data-testid={`tier-${tier.tier_id}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Badge className="bg-[#5C2D91] text-white border-0 text-[10px]">{tier.tier_id.toUpperCase()}</Badge>
                        <Input value={tier.name} onChange={(e) => updateTier(idx, 'name', e.target.value)} className="input-field h-7 text-xs w-[220px]" data-testid={`tier-name-${idx}`} />
                      </div>
                      {formData.network_tiers.length > 1 && (
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeTier(idx)} className="h-7 w-7 p-0 text-[#C24A3B]"><Trash2 className="h-3.5 w-3.5" /></Button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      <div className="space-y-1">
                        <Label className="text-[10px]">Coinsurance (%)</Label>
                        <Input type="number" value={tier.coinsurance} onChange={(e) => updateTier(idx, 'coinsurance', parseFloat(e.target.value) || 0)} className="input-field h-8 text-xs" data-testid={`tier-coins-${idx}`} />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[10px]">Deductible ($)</Label>
                        <Input type="number" value={tier.deductible} onChange={(e) => updateTier(idx, 'deductible', parseFloat(e.target.value) || 0)} className="input-field h-8 text-xs" data-testid={`tier-ded-${idx}`} />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[10px]">OOP Max ($)</Label>
                        <Input type="number" value={tier.oop_max} onChange={(e) => updateTier(idx, 'oop_max', parseFloat(e.target.value) || 0)} className="input-field h-8 text-xs" />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[10px]">Copay Modifier</Label>
                        <Input type="number" step="0.1" value={tier.copay_modifier} onChange={(e) => updateTier(idx, 'copay_modifier', parseFloat(e.target.value) || 1.0)} className="input-field h-8 text-xs" />
                        <p className="text-[9px] text-[#8A8A85]">1.0 = base, 1.5 = 50% higher</p>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[10px]">Description</Label>
                        <Input value={tier.description} onChange={(e) => updateTier(idx, 'description', e.target.value)} className="input-field h-8 text-xs" placeholder="e.g. Contracted PPO" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Reimbursement Logic Reference */}
            {formData.reimbursement_method === 'rbp' && (
              <div className="container-card">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 bg-[#4A6FA5]/10 rounded-lg flex items-center justify-center"><DollarSign className="h-5 w-5 text-[#4A6FA5]" /></div>
                  <div>
                    <h3 className="text-sm font-medium text-[#1C1C1A] font-['Outfit']">Reference Based Pricing Active</h3>
                    <p className="text-[10px] text-[#8A8A85]">Claims auto-adjudicate at <strong>{formData.rbp_medicare_pct}%</strong> of Medicare Fee Schedule</p>
                  </div>
                </div>
                <div className="bg-[#EFF4FB] rounded-lg p-3 text-xs text-[#4A6FA5]">
                  RBP calculates the allowed amount as {formData.rbp_medicare_pct}% of the Medicare rate for each procedure code. This is automatically linked to the system's built-in fee schedule (377+ CPT codes, 87 GPCI localities).
                </div>
              </div>
            )}
          </TabsContent>

          {/* ═══ RISK MANAGEMENT TAB ═══ */}
          <TabsContent value="risk" className="mt-6 space-y-4">
            <div className="container-card">
              <div className="mb-5">
                <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">Stop-Loss & Financial Guardrails</h2>
                <p className="text-xs text-[#8A8A85] mt-1">Define attachment points and auto-flagging thresholds. Claims exceeding the threshold are automatically routed to the Examiner Queue.</p>
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-[#FBEAE7] rounded-xl p-5 border border-[#E8C4BE]" data-testid="risk-specific-section">
                  <div className="flex items-center gap-2 mb-3"><AlertTriangle className="h-4 w-4 text-[#C24A3B]" /><p className="text-sm font-medium text-[#C24A3B]">Specific Stop-Loss</p></div>
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <Label className="text-[10px]">Specific Attachment Point ($)</Label>
                      <Input type="number" value={formData.risk_management?.specific_attachment_point || 0} onChange={(e) => updateRisk('specific_attachment_point', parseFloat(e.target.value) || 0)} className="input-field" data-testid="risk-specific" />
                      <p className="text-[10px] text-[#8A8A85]">Per-member annual threshold before stop-loss kicks in</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px]">Auto-Flag Threshold (%)</Label>
                      <Input type="number" value={formData.risk_management?.auto_flag_threshold_pct || 50} onChange={(e) => updateRisk('auto_flag_threshold_pct', parseFloat(e.target.value) || 50)} className="input-field" data-testid="risk-threshold" />
                      <p className="text-[10px] text-[#8A8A85]">Claims exceeding this % of the Specific limit are flagged in the Examiner Queue</p>
                    </div>
                  </div>
                </div>
                <div className="bg-[#FDF3E1] rounded-xl p-5 border border-[#F5D88E]" data-testid="risk-aggregate-section">
                  <div className="flex items-center gap-2 mb-3"><Shield className="h-4 w-4 text-[#C9862B]" /><p className="text-sm font-medium text-[#C9862B]">Aggregate Stop-Loss</p></div>
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <Label className="text-[10px]">Aggregate Attachment Point ($)</Label>
                      <Input type="number" value={formData.risk_management?.aggregate_attachment_point || 0} onChange={(e) => updateRisk('aggregate_attachment_point', parseFloat(e.target.value) || 0)} className="input-field" data-testid="risk-aggregate" />
                      <p className="text-[10px] text-[#8A8A85]">Group-level annual threshold for total claims</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px]">Stop-Loss Carrier</Label>
                      <Input value={formData.risk_management?.stop_loss_carrier || ''} onChange={(e) => updateRisk('stop_loss_carrier', e.target.value)} className="input-field" placeholder="e.g. Zurich, Swiss Re" data-testid="risk-carrier" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px]">Contract Period</Label>
                      <Select value={formData.risk_management?.contract_period || '12_month'} onValueChange={(v) => updateRisk('contract_period', v)}>
                        <SelectTrigger className="input-field" data-testid="risk-period"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="12_month">12-Month</SelectItem>
                          <SelectItem value="15_month">15-Month (Extended)</SelectItem>
                          <SelectItem value="24_month">24-Month</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              </div>

              {/* Auto-Flag Logic Reference */}
              <div className="mt-5 bg-[#F7F7F4] rounded-xl p-4 border border-[#E2E2DF]">
                <h3 className="text-xs font-medium text-[#64645F] uppercase mb-2">Auto-Flag Logic</h3>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div className="bg-white rounded-lg p-3 border border-[#E2E2DF]">
                    <p className="font-medium text-[#C24A3B] mb-1">Claim Exceeds Threshold</p>
                    <p className="text-[#64645F]">If a claim's paid amount exceeds {formData.risk_management?.auto_flag_threshold_pct || 50}% of {fmt(formData.risk_management?.specific_attachment_point || 0)} = <strong>{fmt((formData.risk_management?.specific_attachment_point || 0) * (formData.risk_management?.auto_flag_threshold_pct || 50) / 100)}</strong>, it is automatically flagged.</p>
                  </div>
                  <div className="bg-white rounded-lg p-3 border border-[#E2E2DF]">
                    <p className="font-medium text-[#C9862B] mb-1">Examiner Queue</p>
                    <p className="text-[#64645F]">Flagged claims appear in the Examiner Queue with a 'STOP-LOSS REVIEW' badge for manual review.</p>
                  </div>
                  <div className="bg-white rounded-lg p-3 border border-[#E2E2DF]">
                    <p className="font-medium text-[#4B6E4E] mb-1">Resolution</p>
                    <p className="text-[#64645F]">Examiner approves, denies, or routes to stop-loss carrier for reimbursement above the attachment point.</p>
                  </div>
                </div>
              </div>

              <div className="mt-3">
                <Label className="text-[10px]">Risk Notes</Label>
                <Textarea value={formData.risk_management?.notes || ''} onChange={(e) => updateRisk('notes', e.target.value)} className="input-field mt-1 text-xs" placeholder="Additional risk management notes..." rows={2} />
              </div>
            </div>
          </TabsContent>

          {/* ═══ EXCLUSIONS TAB ═══ */}
          <TabsContent value="exclusions" className="mt-6">
            <div className="container-card">
              <h2 className="text-lg font-medium text-[#1C1C1A] font-['Outfit'] mb-4">Plan Exclusions</h2>
              <div className="flex gap-2 mb-4">
                <Input value={exclusionInput} onChange={(e) => setExclusionInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addExclusion())} className="input-field" placeholder="Type exclusion and press Enter..." data-testid="exclusion-input" />
                <Button type="button" variant="outline" onClick={addExclusion} data-testid="add-exclusion-btn"><Plus className="h-4 w-4" /></Button>
              </div>
              {formData.exclusions.length === 0 ? (
                <div className="bg-[#F7F7F4] rounded-lg p-4 text-center text-xs text-[#8A8A85]">No exclusions configured</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {formData.exclusions.map((ex, i) => (
                    <Badge key={i} className="bg-[#FBEAE7] text-[#C24A3B] border-0 text-xs px-3 py-1 cursor-pointer hover:bg-[#F5D0C8]" onClick={() => removeExclusion(i)} data-testid={`exclusion-${i}`}>
                      {ex} <Trash2 className="h-3 w-3 ml-1.5 inline" />
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </form>
    </div>
  );
}
