import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { auditAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Settings as SettingsIcon,
  Users,
  Shield,
  History,
  RefreshCw,
} from 'lucide-react';
import { Button } from '../components/ui/button';
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

export default function Settings() {
  const { user } = useAuth();
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const response = await auditAPI.list({ limit: 100 });
      setAuditLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const getActionBadgeClass = (action) => {
    if (action.includes('approved')) return 'badge-approved';
    if (action.includes('denied') || action.includes('delete')) return 'badge-denied';
    if (action.includes('created') || action.includes('register')) return 'badge-pended';
    return 'bg-[#F0F0EA] text-[#64645F]';
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
          Settings
        </h1>
        <p className="text-sm text-[#64645F] mt-1">
          System configuration and audit logs
        </p>
      </div>

      <Tabs defaultValue="audit">
        <TabsList className="bg-[#F0F0EA] p-1">
          <TabsTrigger value="audit" data-testid="tab-audit">
            <History className="h-4 w-4 mr-2" />
            Audit Log
          </TabsTrigger>
          <TabsTrigger value="system" data-testid="tab-system">
            <SettingsIcon className="h-4 w-4 mr-2" />
            System
          </TabsTrigger>
          <TabsTrigger value="roles" data-testid="tab-roles">
            <Shield className="h-4 w-4 mr-2" />
            Roles
          </TabsTrigger>
        </TabsList>

        {/* Audit Log Tab */}
        <TabsContent value="audit" className="mt-6">
          <div className="container-card p-0 overflow-hidden">
            <div className="p-6 border-b border-[#E2E2DF] flex items-center justify-between">
              <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
                System Audit Log
              </h3>
              <Button
                onClick={fetchAuditLogs}
                variant="outline"
                size="sm"
                className="btn-secondary"
                data-testid="refresh-audit-btn"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="table-header">
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.map((log) => (
                    <TableRow key={log.id} className="table-row">
                      <TableCell className="text-xs text-[#64645F]">
                        {new Date(log.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge className={getActionBadgeClass(log.action)}>
                          {log.action.replace(/_/g, ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-['JetBrains_Mono'] text-xs">
                        {log.user_id?.slice(0, 8)}...
                      </TableCell>
                      <TableCell className="text-sm text-[#64645F] max-w-[300px] truncate">
                        {log.details?.claim_number && `Claim: ${log.details.claim_number}`}
                        {log.details?.plan_id && `Plan: ${log.details.plan_id}`}
                        {log.details?.email && `Email: ${log.details.email}`}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* System Tab */}
        <TabsContent value="system" className="mt-6">
          <div className="container-card space-y-6">
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
              System Information
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 bg-[#F7F7F4] rounded-lg">
                <p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">
                  Version
                </p>
                <p className="font-['JetBrains_Mono'] text-sm">FletchFlow v1.0.0</p>
              </div>
              <div className="p-4 bg-[#F7F7F4] rounded-lg">
                <p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">
                  Environment
                </p>
                <p className="font-['JetBrains_Mono'] text-sm">Production</p>
              </div>
              <div className="p-4 bg-[#F7F7F4] rounded-lg">
                <p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">
                  Database
                </p>
                <p className="font-['JetBrains_Mono'] text-sm">MongoDB Connected</p>
              </div>
              <div className="p-4 bg-[#F7F7F4] rounded-lg">
                <p className="text-xs uppercase tracking-[0.2em] text-[#64645F] mb-1">
                  Current User
                </p>
                <p className="font-['JetBrains_Mono'] text-sm">{user?.email}</p>
              </div>
            </div>

            <div className="pt-6 border-t border-[#E2E2DF]">
              <h4 className="font-medium text-[#1C1C1A] mb-4">
                Supported Coverage Lines
              </h4>
              <div className="flex flex-wrap gap-2">
                <Badge className="badge-approved">Medical</Badge>
                <Badge className="badge-pended">Dental (Coming Soon)</Badge>
                <Badge className="badge-pended">Vision (Coming Soon)</Badge>
                <Badge className="badge-pended">Hearing (Coming Soon)</Badge>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles" className="mt-6">
          <div className="container-card space-y-6">
            <h3 className="text-lg font-medium text-[#1C1C1A] font-['Outfit']">
              Role Permissions
            </h3>
            
            <div className="space-y-4">
              <div className="p-4 border border-[#E2E2DF] rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 bg-[#1A3636] rounded flex items-center justify-center">
                    <Shield className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1C1C1A]">Admin</p>
                    <p className="text-xs text-[#64645F]">Full system access</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">Manage Plans</Badge>
                  <Badge variant="outline">Manage Members</Badge>
                  <Badge variant="outline">Adjudicate Claims</Badge>
                  <Badge variant="outline">View Reports</Badge>
                  <Badge variant="outline">System Settings</Badge>
                  <Badge variant="outline">Audit Logs</Badge>
                </div>
              </div>

              <div className="p-4 border border-[#E2E2DF] rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 bg-[#4A6FA5] rounded flex items-center justify-center">
                    <Users className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1C1C1A]">Adjudicator</p>
                    <p className="text-xs text-[#64645F]">Claims processing</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">Add Members</Badge>
                  <Badge variant="outline">Create Claims</Badge>
                  <Badge variant="outline">Adjudicate Claims</Badge>
                  <Badge variant="outline">Resolve Duplicates</Badge>
                  <Badge variant="outline">View Reports</Badge>
                </div>
              </div>

              <div className="p-4 border border-[#E2E2DF] rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 bg-[#8E9F85] rounded flex items-center justify-center">
                    <Users className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1C1C1A]">Reviewer</p>
                    <p className="text-xs text-[#64645F]">Read-only review access</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">View Claims</Badge>
                  <Badge variant="outline">View Members</Badge>
                  <Badge variant="outline">View Plans</Badge>
                  <Badge variant="outline">Resolve Duplicates</Badge>
                </div>
              </div>

              <div className="p-4 border border-[#E2E2DF] rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 bg-[#C9862B] rounded flex items-center justify-center">
                    <History className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1C1C1A]">Auditor</p>
                    <p className="text-xs text-[#64645F]">Compliance and audit access</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">View Claims</Badge>
                  <Badge variant="outline">View Audit Logs</Badge>
                  <Badge variant="outline">View Reports</Badge>
                  <Badge variant="outline">Export Data</Badge>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
