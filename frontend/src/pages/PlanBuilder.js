import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { plansAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Plus,
  Trash2,
  Save,
  RefreshCw,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';

const defaultBenefit = {
  service_category: '',
  covered: true,
  copay: 0,
  coinsurance: 0.2,
  deductible_applies: true,
  annual_max: null,
  visit_limit: null,
  frequency_limit: '',
  waiting_period_days: 0,
  prior_auth_required: false,
  code_range: '',
};

const SERVICE_CATEGORIES = [
  'Preventive Care',
  'Office Visit',
  'Emergency Room',
  'Urgent Care',
  'Hospital Inpatient',
  'Hospital Outpatient',
  'Surgery',
  'Lab & Diagnostics',
  'Imaging',
  'Physical Therapy',
  'Mental Health',
  'Prescription Drugs',
  'Durable Medical Equipment',
  'Specialist Visit',
  'Maternity',
  'Other',
];

export default function PlanBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');
  
  const [formData, setFormData] = useState({
    name: '',
    plan_type: 'medical',
    group_id: '',
    effective_date: new Date().toISOString().split('T')[0],
    termination_date: '',
    deductible_individual: 500,
    deductible_family: 1500,
    oop_max_individual: 5000,
    oop_max_family: 10000,
    network_type: 'PPO',
    reimbursement_method: 'fee_schedule',
    tier_type: 'employee_only',
    benefits: [],
    exclusions: [],
  });

  const [exclusionInput, setExclusionInput] = useState('');

  useEffect(() => {
    if (isEdit) {
      fetchPlan();
    }
  }, [id]);

  const fetchPlan = async () => {
    try {
      const response = await plansAPI.get(id);
      setFormData(response.data);
    } catch (error) {
      console.error('Failed to fetch plan:', error);
      toast.error('Failed to load plan');
      navigate('/plans');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleBenefitChange = (index, field, value) => {
    const newBenefits = [...formData.benefits];
    newBenefits[index] = { ...newBenefits[index], [field]: value };
    setFormData((prev) => ({ ...prev, benefits: newBenefits }));
  };

  const addBenefit = () => {
    setFormData((prev) => ({
      ...prev,
      benefits: [...prev.benefits, { ...defaultBenefit }],
    }));
  };

  const removeBenefit = (index) => {
    const newBenefits = formData.benefits.filter((_, i) => i !== index);
    setFormData((prev) => ({ ...prev, benefits: newBenefits }));
  };

  const addExclusion = () => {
    if (exclusionInput.trim()) {
      setFormData((prev) => ({
        ...prev,
        exclusions: [...prev.exclusions, exclusionInput.trim()],
      }));
      setExclusionInput('');
    }
  };

  const removeExclusion = (index) => {
    const newExclusions = formData.exclusions.filter((_, i) => i !== index);
    setFormData((prev) => ({ ...prev, exclusions: newExclusions }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      if (isEdit) {
        await plansAPI.update(id, formData);
        toast.success('Plan updated successfully');
      } else {
        await plansAPI.create(formData);
        toast.success('Plan created successfully');
      }
      navigate('/plans');
    } catch (error) {
      console.error('Failed to save plan:', error);
      toast.error(error.response?.data?.detail || 'Failed to save plan');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="plan-builder-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/plans')}
            className="hover:bg-[#F0F0EA]"
            data-testid="back-btn"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
              {isEdit ? 'Edit Plan' : 'Create New Plan'}
            </h1>
            <p className="text-sm text-[#64645F] mt-1">
              Configure benefit plan details and coverage rules
            </p>
          </div>
        </div>
        <Button
          onClick={handleSubmit}
          disabled={saving}
          className="btn-primary"
          data-testid="save-plan-btn"
        >
          {saving ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          {isEdit ? 'Update Plan' : 'Create Plan'}
        </Button>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#F0F0EA] p-1">
            <TabsTrigger value="general" data-testid="tab-general">
              General
            </TabsTrigger>
            <TabsTrigger value="cost_sharing" data-testid="tab-cost-sharing">
              Cost Sharing
            </TabsTrigger>
            <TabsTrigger value="benefits" data-testid="tab-benefits">
              Benefits
            </TabsTrigger>
            <TabsTrigger value="exclusions" data-testid="tab-exclusions">
              Exclusions
            </TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="mt-6">
            <div className="container-card space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="name">Plan Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => handleChange('name', e.target.value)}
                    placeholder="e.g., Gold PPO Medical"
                    className="input-field"
                    required
                    data-testid="plan-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="group_id">Group ID</Label>
                  <Input
                    id="group_id"
                    value={formData.group_id}
                    onChange={(e) => handleChange('group_id', e.target.value)}
                    placeholder="e.g., GRP-001"
                    className="input-field"
                    required
                    data-testid="group-id-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="plan_type">Plan Type</Label>
                  <Select
                    value={formData.plan_type}
                    onValueChange={(value) => handleChange('plan_type', value)}
                  >
                    <SelectTrigger data-testid="plan-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="medical">Medical</SelectItem>
                      <SelectItem value="dental">Dental</SelectItem>
                      <SelectItem value="vision">Vision</SelectItem>
                      <SelectItem value="hearing">Hearing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="network_type">Network Type</Label>
                  <Select
                    value={formData.network_type}
                    onValueChange={(value) => handleChange('network_type', value)}
                  >
                    <SelectTrigger data-testid="network-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PPO">PPO</SelectItem>
                      <SelectItem value="HMO">HMO</SelectItem>
                      <SelectItem value="EPO">EPO</SelectItem>
                      <SelectItem value="POS">POS</SelectItem>
                      <SelectItem value="HDHP">HDHP</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="effective_date">Effective Date</Label>
                  <Input
                    id="effective_date"
                    type="date"
                    value={formData.effective_date}
                    onChange={(e) => handleChange('effective_date', e.target.value)}
                    className="input-field"
                    required
                    data-testid="effective-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="termination_date">Termination Date</Label>
                  <Input
                    id="termination_date"
                    type="date"
                    value={formData.termination_date || ''}
                    onChange={(e) => handleChange('termination_date', e.target.value)}
                    className="input-field"
                    data-testid="termination-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reimbursement_method">Reimbursement Method</Label>
                  <Select
                    value={formData.reimbursement_method}
                    onValueChange={(value) => handleChange('reimbursement_method', value)}
                  >
                    <SelectTrigger data-testid="reimbursement-method-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fee_schedule">Fee Schedule</SelectItem>
                      <SelectItem value="percent_medicare">% of Medicare</SelectItem>
                      <SelectItem value="percent_billed">% of Billed</SelectItem>
                      <SelectItem value="rbp">Reference Based Pricing</SelectItem>
                      <SelectItem value="contracted">Contracted Network</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tier_type">Tier Type</Label>
                  <Select
                    value={formData.tier_type}
                    onValueChange={(value) => handleChange('tier_type', value)}
                  >
                    <SelectTrigger data-testid="tier-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="employee_only">Employee Only</SelectItem>
                      <SelectItem value="employee_spouse">Employee + Spouse</SelectItem>
                      <SelectItem value="employee_child">Employee + Child(ren)</SelectItem>
                      <SelectItem value="family">Family</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Cost Sharing Tab */}
          <TabsContent value="cost_sharing" className="mt-6">
            <div className="container-card space-y-6">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
                Deductibles & Out-of-Pocket Maximums
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="deductible_individual">Individual Deductible</Label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8A85]">$</span>
                    <Input
                      id="deductible_individual"
                      type="number"
                      value={formData.deductible_individual}
                      onChange={(e) => handleChange('deductible_individual', parseFloat(e.target.value))}
                      className="input-field pl-8"
                      min="0"
                      data-testid="deductible-individual-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="deductible_family">Family Deductible</Label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8A85]">$</span>
                    <Input
                      id="deductible_family"
                      type="number"
                      value={formData.deductible_family}
                      onChange={(e) => handleChange('deductible_family', parseFloat(e.target.value))}
                      className="input-field pl-8"
                      min="0"
                      data-testid="deductible-family-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="oop_max_individual">Individual OOP Max</Label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8A85]">$</span>
                    <Input
                      id="oop_max_individual"
                      type="number"
                      value={formData.oop_max_individual}
                      onChange={(e) => handleChange('oop_max_individual', parseFloat(e.target.value))}
                      className="input-field pl-8"
                      min="0"
                      data-testid="oop-max-individual-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="oop_max_family">Family OOP Max</Label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8A85]">$</span>
                    <Input
                      id="oop_max_family"
                      type="number"
                      value={formData.oop_max_family}
                      onChange={(e) => handleChange('oop_max_family', parseFloat(e.target.value))}
                      className="input-field pl-8"
                      min="0"
                      data-testid="oop-max-family-input"
                    />
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Benefits Tab */}
          <TabsContent value="benefits" className="mt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
                  Service Benefits
                </h3>
                <Button
                  type="button"
                  onClick={addBenefit}
                  variant="outline"
                  className="btn-secondary"
                  data-testid="add-benefit-btn"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Benefit
                </Button>
              </div>

              {formData.benefits.length === 0 ? (
                <div className="container-card text-center py-12">
                  <p className="text-[#64645F] mb-2">No benefits configured</p>
                  <p className="text-sm text-[#8A8A85]">
                    Add service categories and configure coverage rules
                  </p>
                </div>
              ) : (
                formData.benefits.map((benefit, index) => (
                  <div
                    key={index}
                    className="container-card"
                    data-testid={`benefit-${index}`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <h4 className="font-medium text-[#1C1C1A]">
                        Benefit {index + 1}
                      </h4>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeBenefit(index)}
                        className="text-[#C24A3B] hover:text-[#A33C2F] hover:bg-[#FBEAE7]"
                        data-testid={`remove-benefit-${index}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>Service Category</Label>
                        <Select
                          value={benefit.service_category}
                          onValueChange={(value) => handleBenefitChange(index, 'service_category', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select category" />
                          </SelectTrigger>
                          <SelectContent>
                            {SERVICE_CATEGORIES.map((cat) => (
                              <SelectItem key={cat} value={cat}>
                                {cat}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Copay</Label>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8A85]">$</span>
                          <Input
                            type="number"
                            value={benefit.copay}
                            onChange={(e) => handleBenefitChange(index, 'copay', parseFloat(e.target.value))}
                            className="input-field pl-8"
                            min="0"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Coinsurance</Label>
                        <div className="relative">
                          <Input
                            type="number"
                            value={benefit.coinsurance * 100}
                            onChange={(e) => handleBenefitChange(index, 'coinsurance', parseFloat(e.target.value) / 100)}
                            className="input-field pr-8"
                            min="0"
                            max="100"
                          />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8A8A85]">%</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Code Range (Optional)</Label>
                        <Input
                          value={benefit.code_range || ''}
                          onChange={(e) => handleBenefitChange(index, 'code_range', e.target.value)}
                          placeholder="e.g., 99201"
                          className="input-field font-['JetBrains_Mono'] text-xs"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Visit Limit</Label>
                        <Input
                          type="number"
                          value={benefit.visit_limit || ''}
                          onChange={(e) => handleBenefitChange(index, 'visit_limit', e.target.value ? parseInt(e.target.value) : null)}
                          placeholder="Unlimited"
                          className="input-field"
                          min="0"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Waiting Period (Days)</Label>
                        <Input
                          type="number"
                          value={benefit.waiting_period_days}
                          onChange={(e) => handleBenefitChange(index, 'waiting_period_days', parseInt(e.target.value))}
                          className="input-field"
                          min="0"
                        />
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-6 mt-4 pt-4 border-t border-[#E2E2DF]">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={benefit.covered}
                          onCheckedChange={(checked) => handleBenefitChange(index, 'covered', checked)}
                        />
                        <Label>Covered</Label>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={benefit.deductible_applies}
                          onCheckedChange={(checked) => handleBenefitChange(index, 'deductible_applies', checked)}
                        />
                        <Label>Deductible Applies</Label>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={benefit.prior_auth_required}
                          onCheckedChange={(checked) => handleBenefitChange(index, 'prior_auth_required', checked)}
                        />
                        <Label>Prior Auth Required</Label>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </TabsContent>

          {/* Exclusions Tab */}
          <TabsContent value="exclusions" className="mt-6">
            <div className="container-card space-y-6">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
                Excluded Services
              </h3>
              <p className="text-sm text-[#64645F]">
                Add CPT/HCPCS codes that are not covered under this plan
              </p>

              <div className="flex gap-3">
                <Input
                  value={exclusionInput}
                  onChange={(e) => setExclusionInput(e.target.value)}
                  placeholder="Enter CPT code (e.g., 99999)"
                  className="input-field font-['JetBrains_Mono'] text-xs max-w-xs"
                  data-testid="exclusion-input"
                />
                <Button
                  type="button"
                  onClick={addExclusion}
                  variant="outline"
                  className="btn-secondary"
                  data-testid="add-exclusion-btn"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add
                </Button>
              </div>

              {formData.exclusions.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {formData.exclusions.map((code, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 px-3 py-1.5 bg-[#FBEAE7] rounded-lg"
                    >
                      <span className="font-['JetBrains_Mono'] text-xs text-[#C24A3B]">
                        {code}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeExclusion(index)}
                        className="text-[#C24A3B] hover:text-[#A33C2F]"
                        data-testid={`remove-exclusion-${index}`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
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
