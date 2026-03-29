import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  FileText,
  Users,
  AlertTriangle,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Building2,
  ChevronDown,
  Calculator,
  Shield,
  Globe,
  Database,
  Heart,
  Briefcase,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Button } from './ui/button';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Claims', href: '/claims', icon: FileText },
  { name: 'Plans', href: '/plans', icon: Building2 },
  { name: 'Groups', href: '/groups', icon: Briefcase },
  { name: 'Members', href: '/members', icon: Users },
  { name: 'Prior Auth', href: '/prior-auth', icon: Shield },
  { name: 'Preventive', href: '/preventive', icon: Heart },
  { name: 'Network', href: '/network', icon: Globe },
  { name: 'Code Database', href: '/code-database', icon: Database },
  { name: 'Fee Schedule', href: '/fee-schedule', icon: Calculator },
  { name: 'Duplicates', href: '/duplicates', icon: AlertTriangle },
  { name: 'Reports', href: '/reports', icon: BarChart3 },
];

const adminNav = [
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name) => {
    return name
      ?.split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase() || 'U';
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin':
        return 'bg-[#1A3636] text-white';
      case 'adjudicator':
        return 'bg-[#4A6FA5] text-white';
      case 'reviewer':
        return 'bg-[#8E9F85] text-white';
      case 'auditor':
        return 'bg-[#C9862B] text-white';
      default:
        return 'bg-[#E2E2DF] text-[#1C1C1A]';
    }
  };

  const NavItem = ({ item }) => (
    <NavLink
      to={item.href}
      className={({ isActive }) =>
        `nav-item ${isActive ? 'nav-item-active' : 'nav-item-inactive'}`
      }
      onClick={() => setSidebarOpen(false)}
      data-testid={`nav-${item.name.toLowerCase()}`}
    >
      <item.icon className="h-5 w-5" />
      <span>{item.name}</span>
    </NavLink>
  );

  return (
    <div className="min-h-screen bg-[#F7F7F4]">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-white border-r border-[#E2E2DF] transform transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-[#E2E2DF]">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#1A3636] rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm font-['Outfit']">F</span>
              </div>
              <span className="text-lg font-semibold text-[#1C1C1A] font-['Outfit']">FletchFlow</span>
            </div>
            <button
              className="lg:hidden text-[#64645F] hover:text-[#1C1C1A]"
              onClick={() => setSidebarOpen(false)}
              data-testid="close-sidebar-btn"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => (
              <NavItem key={item.name} item={item} />
            ))}
            
            {user?.role === 'admin' && (
              <>
                <div className="pt-4 pb-2">
                  <div className="px-4 text-xs uppercase tracking-[0.2em] text-[#8A8A85] font-medium">
                    Admin
                  </div>
                </div>
                {adminNav.map((item) => (
                  <NavItem key={item.name} item={item} />
                ))}
              </>
            )}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-[#E2E2DF]">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button 
                  className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-[#F0F0EA] transition-colors"
                  data-testid="user-menu-btn"
                >
                  <Avatar className="h-9 w-9">
                    <AvatarFallback className="bg-[#1A3636] text-white text-sm">
                      {getInitials(user?.name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 text-left">
                    <div className="text-sm font-medium text-[#1C1C1A] truncate">
                      {user?.name}
                    </div>
                    <div className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase tracking-wider font-semibold ${getRoleBadgeColor(user?.role)}`}>
                      {user?.role}
                    </div>
                  </div>
                  <ChevronDown className="h-4 w-4 text-[#8A8A85]" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium">{user?.name}</p>
                  <p className="text-xs text-[#64645F]">{user?.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={handleLogout}
                  className="text-[#C24A3B] focus:text-[#C24A3B]"
                  data-testid="logout-btn"
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-white border-b border-[#E2E2DF] flex items-center px-4 lg:px-8">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden mr-4"
            onClick={() => setSidebarOpen(true)}
            data-testid="open-sidebar-btn"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex-1" />
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
