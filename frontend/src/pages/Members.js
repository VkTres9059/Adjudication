import { useState, useEffect } from 'react';
import { membersAPI, ediAPI } from '../lib/api';
import { toast } from 'sonner';
import {
  Search,
  Plus,
  Users,
  RefreshCw,
  Upload,
  User,
  ChevronRight,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

export default function Members() {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAddMember, setShowAddMember] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [newMember, setNewMember] = useState({
    member_id: '',
    first_name: '',
    last_name: '',
    dob: '',
    gender: 'M',
    group_id: '',
    plan_id: '',
    effective_date: new Date().toISOString().split('T')[0],
    relationship: 'subscriber',
  });

  const fetchMembers = async () => {
    setLoading(true);
    try {
      const params = search ? { search } : {};
      const response = await membersAPI.list(params);
      setMembers(response.data);
    } catch (error) {
      console.error('Failed to fetch members:', error);
      toast.error('Failed to load members');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, []);

  const handleSearch = () => {
    fetchMembers();
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await membersAPI.create(newMember);
      toast.success('Member added successfully');
      setShowAddMember(false);
      setNewMember({
        member_id: '',
        first_name: '',
        last_name: '',
        dob: '',
        gender: 'M',
        group_id: '',
        plan_id: '',
        effective_date: new Date().toISOString().split('T')[0],
        relationship: 'subscriber',
      });
      fetchMembers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add member');
    } finally {
      setSaving(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const response = await ediAPI.upload834(file);
      toast.success(`Uploaded successfully: ${response.data.members_created} members created`);
      if (response.data.errors?.length > 0) {
        toast.warning(`${response.data.errors.length} errors occurred`);
      }
      setShowUpload(false);
      fetchMembers();
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const filteredMembers = members.filter((member) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      member.member_id.toLowerCase().includes(searchLower) ||
      member.first_name.toLowerCase().includes(searchLower) ||
      member.last_name.toLowerCase().includes(searchLower)
    );
  });

  return (
    <div className="space-y-6" data-testid="members-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#1C1C1A] font-['Outfit'] tracking-tight">
            Members
          </h1>
          <p className="text-sm text-[#64645F] mt-1">
            Manage member eligibility and enrollment
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            onClick={() => setShowUpload(true)}
            variant="outline"
            className="btn-secondary"
            data-testid="upload-834-btn"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload 834
          </Button>
          <Button
            onClick={() => setShowAddMember(true)}
            className="btn-primary"
            data-testid="add-member-btn"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Member
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="container-card">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8A85]" />
            <Input
              placeholder="Search by member ID, name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="pl-10 input-field"
              data-testid="members-search-input"
            />
          </div>
          <Button onClick={handleSearch} className="btn-primary" data-testid="search-btn">
            Search
          </Button>
          <Button
            variant="outline"
            onClick={fetchMembers}
            className="btn-secondary"
            data-testid="refresh-members-btn"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Members Table */}
      <div className="container-card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-8 w-8 text-[#1A3636] animate-spin" />
          </div>
        ) : filteredMembers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Users className="h-12 w-12 text-[#E2E2DF] mb-4" />
            <p className="text-[#64645F] mb-2">No members found</p>
            <p className="text-sm text-[#8A8A85]">
              Add members manually or upload an 834 file
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="table-header">
                <TableHead>Member ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>DOB</TableHead>
                <TableHead>Group</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Effective</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMembers.map((member) => (
                <TableRow
                  key={member.id}
                  className="table-row hover:bg-[#F7F7F4] transition-colors"
                  data-testid={`member-row-${member.id}`}
                >
                  <TableCell className="font-['JetBrains_Mono'] text-xs">
                    {member.member_id}
                  </TableCell>
                  <TableCell className="font-medium">
                    {member.first_name} {member.last_name}
                  </TableCell>
                  <TableCell>{member.dob}</TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs">
                    {member.group_id}
                  </TableCell>
                  <TableCell className="font-['JetBrains_Mono'] text-xs max-w-[100px] truncate">
                    {member.plan_id}
                  </TableCell>
                  <TableCell>{member.effective_date}</TableCell>
                  <TableCell>
                    <Badge className={member.status === 'active' ? 'badge-approved' : 'badge-denied'}>
                      {member.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon">
                      <ChevronRight className="h-4 w-4 text-[#8A8A85]" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Summary */}
      <div className="text-sm text-[#64645F]">
        Showing {filteredMembers.length} of {members.length} members
      </div>

      {/* Add Member Modal */}
      <Dialog open={showAddMember} onOpenChange={setShowAddMember}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Add New Member</DialogTitle>
            <DialogDescription>
              Enter member details to create a new enrollment
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAddMember}>
            <div className="grid grid-cols-2 gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="member_id">Member ID</Label>
                <Input
                  id="member_id"
                  value={newMember.member_id}
                  onChange={(e) => setNewMember({ ...newMember, member_id: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-id-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input
                  id="first_name"
                  value={newMember.first_name}
                  onChange={(e) => setNewMember({ ...newMember, first_name: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-first-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  value={newMember.last_name}
                  onChange={(e) => setNewMember({ ...newMember, last_name: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-last-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dob">Date of Birth</Label>
                <Input
                  id="dob"
                  type="date"
                  value={newMember.dob}
                  onChange={(e) => setNewMember({ ...newMember, dob: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-dob-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gender">Gender</Label>
                <Select
                  value={newMember.gender}
                  onValueChange={(value) => setNewMember({ ...newMember, gender: value })}
                >
                  <SelectTrigger data-testid="new-member-gender-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="M">Male</SelectItem>
                    <SelectItem value="F">Female</SelectItem>
                    <SelectItem value="O">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="relationship">Relationship</Label>
                <Select
                  value={newMember.relationship}
                  onValueChange={(value) => setNewMember({ ...newMember, relationship: value })}
                >
                  <SelectTrigger data-testid="new-member-relationship-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="subscriber">Subscriber</SelectItem>
                    <SelectItem value="spouse">Spouse</SelectItem>
                    <SelectItem value="child">Child</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="group_id">Group ID</Label>
                <Input
                  id="group_id"
                  value={newMember.group_id}
                  onChange={(e) => setNewMember({ ...newMember, group_id: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-group-id-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="plan_id">Plan ID</Label>
                <Input
                  id="plan_id"
                  value={newMember.plan_id}
                  onChange={(e) => setNewMember({ ...newMember, plan_id: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-plan-id-input"
                />
              </div>
              <div className="space-y-2 col-span-2">
                <Label htmlFor="effective_date">Effective Date</Label>
                <Input
                  id="effective_date"
                  type="date"
                  value={newMember.effective_date}
                  onChange={(e) => setNewMember({ ...newMember, effective_date: e.target.value })}
                  className="input-field"
                  required
                  data-testid="new-member-effective-date-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAddMember(false)}
                className="btn-secondary"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={saving} className="btn-primary" data-testid="save-member-btn">
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Add Member'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Upload 834 Modal */}
      <Dialog open={showUpload} onOpenChange={setShowUpload}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Upload EDI 834</DialogTitle>
            <DialogDescription>
              Upload an EDI 834 enrollment file to bulk import members
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="border-2 border-dashed border-[#E2E2DF] rounded-xl p-8 text-center">
              <Upload className="h-10 w-10 text-[#8A8A85] mx-auto mb-4" />
              <p className="text-sm text-[#64645F] mb-4">
                Drag and drop your 834 file, or click to browse
              </p>
              <input
                type="file"
                accept=".txt,.edi,.834"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
                data-testid="file-upload-input"
              />
              <label htmlFor="file-upload">
                <Button
                  type="button"
                  variant="outline"
                  className="btn-secondary"
                  disabled={uploading}
                  asChild
                >
                  <span>
                    {uploading ? (
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4 mr-2" />
                    )}
                    {uploading ? 'Uploading...' : 'Select File'}
                  </span>
                </Button>
              </label>
            </div>
            <div className="mt-4 p-3 bg-[#EEF3F9] rounded-lg">
              <p className="text-xs text-[#4A6FA5] font-medium mb-1">Expected Format</p>
              <p className="text-xs text-[#64645F] font-['JetBrains_Mono']">
                MemberID|FirstName|LastName|DOB|Gender|GroupID|PlanID|EffDate
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
