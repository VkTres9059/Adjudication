import { useState } from 'react';
import { claimsAPI } from '../lib/api';
import { toast } from 'sonner';
import { Plus, Trash2, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

const defaultServiceLine = {
  line_number: 1,
  cpt_code: '',
  modifier: '',
  units: 1,
  billed_amount: 0,
  service_date: '',
  diagnosis_codes: [],
  place_of_service: '11',
};

export default function NewClaimModal({ open, onClose, onSuccess }) {
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    member_id: '',
    provider_npi: '',
    provider_name: '',
    claim_type: 'medical',
    service_date_from: '',
    service_date_to: '',
    total_billed: 0,
    diagnosis_codes: [''],
    service_lines: [{ ...defaultServiceLine }],
    prior_auth_number: '',
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleServiceLineChange = (index, field, value) => {
    const newLines = [...formData.service_lines];
    newLines[index] = { ...newLines[index], [field]: value };
    
    // Update line numbers
    newLines.forEach((line, i) => {
      line.line_number = i + 1;
    });
    
    // Calculate total billed
    const totalBilled = newLines.reduce((sum, line) => sum + (parseFloat(line.billed_amount) || 0), 0);
    
    setFormData((prev) => ({
      ...prev,
      service_lines: newLines,
      total_billed: totalBilled,
    }));
  };

  const addServiceLine = () => {
    setFormData((prev) => ({
      ...prev,
      service_lines: [
        ...prev.service_lines,
        {
          ...defaultServiceLine,
          line_number: prev.service_lines.length + 1,
          service_date: prev.service_date_from,
        },
      ],
    }));
  };

  const removeServiceLine = (index) => {
    if (formData.service_lines.length === 1) return;
    
    const newLines = formData.service_lines.filter((_, i) => i !== index);
    newLines.forEach((line, i) => {
      line.line_number = i + 1;
    });
    
    const totalBilled = newLines.reduce((sum, line) => sum + (parseFloat(line.billed_amount) || 0), 0);
    
    setFormData((prev) => ({
      ...prev,
      service_lines: newLines,
      total_billed: totalBilled,
    }));
  };

  const handleDiagnosisChange = (index, value) => {
    const newCodes = [...formData.diagnosis_codes];
    newCodes[index] = value;
    setFormData((prev) => ({ ...prev, diagnosis_codes: newCodes }));
  };

  const addDiagnosis = () => {
    setFormData((prev) => ({
      ...prev,
      diagnosis_codes: [...prev.diagnosis_codes, ''],
    }));
  };

  const removeDiagnosis = (index) => {
    if (formData.diagnosis_codes.length === 1) return;
    const newCodes = formData.diagnosis_codes.filter((_, i) => i !== index);
    setFormData((prev) => ({ ...prev, diagnosis_codes: newCodes }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      // Prepare data
      const submitData = {
        ...formData,
        diagnosis_codes: formData.diagnosis_codes.filter((c) => c.trim()),
        service_lines: formData.service_lines.map((line) => ({
          ...line,
          billed_amount: parseFloat(line.billed_amount) || 0,
          units: parseInt(line.units) || 1,
          diagnosis_codes: formData.diagnosis_codes.filter((c) => c.trim()),
        })),
      };

      await claimsAPI.create(submitData);
      toast.success('Claim created successfully');
      onSuccess();
      
      // Reset form
      setFormData({
        member_id: '',
        provider_npi: '',
        provider_name: '',
        claim_type: 'medical',
        service_date_from: '',
        service_date_to: '',
        total_billed: 0,
        diagnosis_codes: [''],
        service_lines: [{ ...defaultServiceLine }],
        prior_auth_number: '',
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create claim');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-['Outfit']">Create New Claim</DialogTitle>
          <DialogDescription>
            Enter claim details for adjudication
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-6 py-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="member_id">Member ID *</Label>
                <Input
                  id="member_id"
                  value={formData.member_id}
                  onChange={(e) => handleChange('member_id', e.target.value)}
                  className="input-field font-['JetBrains_Mono'] text-xs"
                  placeholder="e.g., MEM001"
                  required
                  data-testid="claim-member-id-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="claim_type">Claim Type *</Label>
                <Select
                  value={formData.claim_type}
                  onValueChange={(value) => handleChange('claim_type', value)}
                >
                  <SelectTrigger data-testid="claim-type-select">
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
            </div>

            {/* Provider Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="provider_npi">Provider NPI *</Label>
                <Input
                  id="provider_npi"
                  value={formData.provider_npi}
                  onChange={(e) => handleChange('provider_npi', e.target.value)}
                  className="input-field font-['JetBrains_Mono'] text-xs"
                  placeholder="e.g., 1234567890"
                  required
                  data-testid="claim-provider-npi-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="provider_name">Provider Name *</Label>
                <Input
                  id="provider_name"
                  value={formData.provider_name}
                  onChange={(e) => handleChange('provider_name', e.target.value)}
                  className="input-field"
                  placeholder="e.g., ABC Medical Center"
                  required
                  data-testid="claim-provider-name-input"
                />
              </div>
            </div>

            {/* Dates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="service_date_from">Service Date From *</Label>
                <Input
                  id="service_date_from"
                  type="date"
                  value={formData.service_date_from}
                  onChange={(e) => {
                    handleChange('service_date_from', e.target.value);
                    if (!formData.service_date_to) {
                      handleChange('service_date_to', e.target.value);
                    }
                  }}
                  className="input-field"
                  required
                  data-testid="claim-date-from-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="service_date_to">Service Date To *</Label>
                <Input
                  id="service_date_to"
                  type="date"
                  value={formData.service_date_to}
                  onChange={(e) => handleChange('service_date_to', e.target.value)}
                  className="input-field"
                  required
                  data-testid="claim-date-to-input"
                />
              </div>
            </div>

            {/* Prior Auth */}
            <div className="space-y-2">
              <Label htmlFor="prior_auth_number">Prior Authorization Number</Label>
              <Input
                id="prior_auth_number"
                value={formData.prior_auth_number}
                onChange={(e) => handleChange('prior_auth_number', e.target.value)}
                className="input-field font-['JetBrains_Mono'] text-xs"
                placeholder="Optional"
                data-testid="claim-prior-auth-input"
              />
            </div>

            {/* Diagnosis Codes */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Diagnosis Codes (ICD-10) *</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={addDiagnosis}
                  className="text-xs"
                  data-testid="add-diagnosis-btn"
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.diagnosis_codes.map((code, index) => (
                  <div key={index} className="flex items-center gap-1">
                    <Input
                      value={code}
                      onChange={(e) => handleDiagnosisChange(index, e.target.value)}
                      className="input-field font-['JetBrains_Mono'] text-xs w-28"
                      placeholder="e.g., J06.9"
                      data-testid={`diagnosis-${index}-input`}
                    />
                    {formData.diagnosis_codes.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeDiagnosis(index)}
                        className="h-8 w-8 text-[#C24A3B]"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Service Lines */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Service Lines *</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addServiceLine}
                  className="btn-secondary text-xs"
                  data-testid="add-service-line-btn"
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Add Line
                </Button>
              </div>

              {formData.service_lines.map((line, index) => (
                <div
                  key={index}
                  className="p-4 bg-[#F7F7F4] rounded-lg space-y-3"
                  data-testid={`service-line-${index}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-[#64645F]">
                      Line {line.line_number}
                    </span>
                    {formData.service_lines.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeServiceLine(index)}
                        className="h-6 w-6 text-[#C24A3B]"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-4 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">CPT/HCPCS *</Label>
                      <Input
                        value={line.cpt_code}
                        onChange={(e) => handleServiceLineChange(index, 'cpt_code', e.target.value)}
                        className="input-field font-['JetBrains_Mono'] text-xs"
                        placeholder="99213"
                        required
                        data-testid={`line-${index}-cpt-input`}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Modifier</Label>
                      <Input
                        value={line.modifier}
                        onChange={(e) => handleServiceLineChange(index, 'modifier', e.target.value)}
                        className="input-field font-['JetBrains_Mono'] text-xs"
                        placeholder="25"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Units *</Label>
                      <Input
                        type="number"
                        value={line.units}
                        onChange={(e) => handleServiceLineChange(index, 'units', e.target.value)}
                        className="input-field"
                        min="1"
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Billed Amount *</Label>
                      <div className="relative">
                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[#8A8A85] text-xs">$</span>
                        <Input
                          type="number"
                          value={line.billed_amount}
                          onChange={(e) => handleServiceLineChange(index, 'billed_amount', e.target.value)}
                          className="input-field pl-6"
                          min="0"
                          step="0.01"
                          required
                          data-testid={`line-${index}-amount-input`}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Total */}
              <div className="flex justify-end pt-2">
                <div className="text-right">
                  <span className="text-xs text-[#64645F]">Total Billed: </span>
                  <span className="text-lg font-semibold text-[#1C1C1A] font-['Outfit']">
                    ${formData.total_billed.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={saving}
              className="btn-primary"
              data-testid="submit-claim-btn"
            >
              {saving ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Create Claim
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
