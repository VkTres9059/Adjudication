import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
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
import { toast } from 'sonner';
import { Eye, EyeOff, LogIn, UserPlus } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'reviewer',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isRegister) {
        await register(formData.email, formData.password, formData.name, formData.role);
        toast.success('Account created successfully');
      } else {
        await login(formData.email, formData.password);
        toast.success('Welcome back!');
      }
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-[#F7F7F4] flex">
      {/* Left side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-[#1A3636] rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-xl font-['Outfit']">F</span>
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-[#1C1C1A] font-['Outfit']">FletchFlow</h1>
              <p className="text-sm text-[#64645F]">Claims Adjudication System</p>
            </div>
          </div>

          {/* Form */}
          <div className="bg-white border border-[#E2E2DF] rounded-xl p-8">
            <h2 className="text-xl font-semibold text-[#1C1C1A] font-['Outfit'] mb-2">
              {isRegister ? 'Create your account' : 'Sign in to your account'}
            </h2>
            <p className="text-sm text-[#64645F] mb-8">
              {isRegister
                ? 'Get started with FletchFlow claims platform'
                : 'Enter your credentials to access the dashboard'}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {isRegister && (
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-sm font-medium text-[#1C1C1A]">
                    Full Name
                  </Label>
                  <Input
                    id="name"
                    name="name"
                    type="text"
                    placeholder="John Smith"
                    value={formData.name}
                    onChange={handleChange}
                    className="input-field"
                    required
                    data-testid="register-name-input"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-[#1C1C1A]">
                  Email Address
                </Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="john@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  className="input-field"
                  required
                  data-testid="login-email-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium text-[#1C1C1A]">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    className="input-field pr-10"
                    required
                    data-testid="login-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8A8A85] hover:text-[#1C1C1A]"
                    data-testid="toggle-password-btn"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {isRegister && (
                <div className="space-y-2">
                  <Label htmlFor="role" className="text-sm font-medium text-[#1C1C1A]">
                    Role
                  </Label>
                  <Select
                    value={formData.role}
                    onValueChange={(value) => setFormData({ ...formData, role: value })}
                  >
                    <SelectTrigger data-testid="register-role-select" className="input-field">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="reviewer">Reviewer</SelectItem>
                      <SelectItem value="adjudicator">Adjudicator</SelectItem>
                      <SelectItem value="auditor">Auditor</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              <Button
                type="submit"
                className="w-full btn-primary h-11"
                disabled={loading}
                data-testid="login-submit-btn"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    {isRegister ? 'Creating account...' : 'Signing in...'}
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    {isRegister ? <UserPlus className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
                    {isRegister ? 'Create Account' : 'Sign In'}
                  </span>
                )}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => setIsRegister(!isRegister)}
                className="text-sm text-[#1A3636] hover:text-[#2A4B4B] font-medium"
                data-testid="toggle-auth-mode-btn"
              >
                {isRegister
                  ? 'Already have an account? Sign in'
                  : "Don't have an account? Create one"}
              </button>
            </div>
          </div>

          {/* Demo credentials hint */}
          <div className="mt-6 p-4 bg-[#EEF3F9] border border-[#4A6FA5]/20 rounded-lg">
            <p className="text-xs text-[#4A6FA5] font-medium mb-1">Demo Mode</p>
            <p className="text-xs text-[#64645F]">
              Create an account with any email to get started. Use role "admin" for full access.
            </p>
          </div>
        </div>
      </div>

      {/* Right side - Hero */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#1A3636] items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#8E9F85] rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
        </div>
        
        <div className="relative z-10 max-w-lg text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 rounded-full text-white/80 text-sm mb-8">
            <span className="w-2 h-2 bg-[#8E9F85] rounded-full animate-pulse" />
            Enterprise Claims Platform
          </div>
          
          <h2 className="text-4xl font-bold text-white font-['Outfit'] mb-6">
            Intelligent Claims Adjudication
          </h2>
          
          <p className="text-lg text-white/70 mb-12">
            Multi-line claims adjudication with real-time duplicate detection, 
            Medicare fee schedule pricing, and EDI 834/837/835 processing.
          </p>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-left">
              <div className="text-3xl font-bold text-white font-['Outfit'] mb-1">4</div>
              <div className="text-sm text-white/60">Coverage lines</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-left">
              <div className="text-3xl font-bold text-white font-['Outfit'] mb-1">377+</div>
              <div className="text-sm text-white/60">Procedure codes</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-left">
              <div className="text-3xl font-bold text-white font-['Outfit'] mb-1">87</div>
              <div className="text-sm text-white/60">GPCI localities</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-left">
              <div className="text-3xl font-bold text-white font-['Outfit'] mb-1">X12</div>
              <div className="text-sm text-white/60">EDI compliant</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
