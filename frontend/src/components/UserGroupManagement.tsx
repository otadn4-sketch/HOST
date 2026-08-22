import React, { useState } from 'react';
import { 
  Users, 
  Building2, 
  UserPlus, 
  FolderPlus, 
  ShieldCheck, 
  Lock, 
  KeyRound, 
  CheckCircle2, 
  XCircle, 
  Edit3, 
  Trash2, 
  Search, 
  Mail, 
  Phone, 
  Layers, 
  HardDrive,
  X
} from 'lucide-react';
import { User, Department, UserRole, UserStatus } from '../types';
import { StorageService } from '../services/storageService';
import { DataApi } from '../services/api';

interface UserGroupManagementProps {
  users: User[];
  departments: Department[];
  currentUser: User;
  onRefresh: () => void;
}

export const UserGroupManagement: React.FC<UserGroupManagementProps> = ({
  users,
  departments,
  currentUser,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<'users' | 'departments'>('users');
  const [userSearch, setUserSearch] = useState('');
  const [selectedDeptFilter, setSelectedDeptFilter] = useState('all');
  
  // Modals state
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [showAddDeptModal, setShowAddDeptModal] = useState(false);
  const [showResetPassModal, setShowResetPassModal] = useState<User | null>(null);

  // New User Form State
  const [newUsername, setNewUsername] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('user');
  const [newDeptId, setNewDeptId] = useState(departments[0]?.id || '');
  const [newPassword, setNewPassword] = useState('');

  // New Department Form State
  const [newDeptName, setNewDeptName] = useState('');
  const [newDeptCode, setNewDeptCode] = useState('');
  const [newDeptManager, setNewDeptManager] = useState('');
  const [newDeptMaxSize, setNewDeptMaxSize] = useState(50);
  const [newDeptDesc, setNewDeptDesc] = useState('');

  const isAdmin = currentUser.role === 'system_admin';

  // Filter users
  const filteredUsers = users.filter(u => {
    if (userSearch.trim()) {
      const q = userSearch.toLowerCase();
      const matches = 
        u.fullName.toLowerCase().includes(q) ||
        u.username.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.departmentName.toLowerCase().includes(q);
      if (!matches) return false;
    }
    if (selectedDeptFilter !== 'all' && u.departmentId !== selectedDeptFilter) return false;
    return true;
  });

  const handleToggleUserStatus = async (user: User) => {
    const newStatus: UserStatus = user.status === 'active' ? 'suspended' : 'active';
    await DataApi.patchUser(user.id, { status: newStatus });
    onRefresh();
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newFullName.trim() || !newPassword) return;
    await DataApi.createUser({
      username: newUsername.trim(),
      full_name: newFullName.trim(),
      email: newEmail.trim() || `${newUsername.trim()}@eytan.local`,
      phone_number: newPhone.trim() || null,
      role: newRole,
      group_id: newDeptId,
      password: newPassword,
    });
    setShowAddUserModal(false);
    setNewUsername('');
    setNewFullName('');
    setNewEmail('');
    setNewPhone('');
    setNewPassword('');
    onRefresh();
  };

  const handleCreateDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDeptName.trim() || !newDeptCode.trim()) return;
    await DataApi.createGroup({
      name: newDeptName.trim(),
      code: newDeptCode.trim().toUpperCase(),
      description: newDeptDesc.trim(),
      max_file_size_mb: Number(newDeptMaxSize) || 50,
      allowed_file_extensions: ['pdf', 'xlsx', 'docx', 'pptx', 'txt'],
    });
    setShowAddDeptModal(false);
    setNewDeptName('');
    setNewDeptCode('');
    setNewDeptManager('');
    setNewDeptDesc('');
    onRefresh();
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showResetPassModal || !newPassword) return;
    await DataApi.resetPassword(showResetPassModal.id, newPassword);
    setShowResetPassModal(null);
    setNewPassword('');
    onRefresh();
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Tabs */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-600" />
              <span>مدیریت کاربران، نقش‌ها و ساختار گروه‌ها</span>
            </h1>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === 'users' && (
              <button
                onClick={() => setShowAddUserModal(true)}
                className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-xs"
              >
                <UserPlus className="w-4 h-4" />
                <span>تعریف کاربر جدید</span>
              </button>
            )}

            {activeTab === 'departments' && isAdmin && (
              <button
                onClick={() => setShowAddDeptModal(true)}
                className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-xs"
              >
                <FolderPlus className="w-4 h-4" />
                <span>افزودن واحد سازمانی</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 border-t border-slate-100 pt-3">
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              activeTab === 'users'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:text-slate-900'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>حساب‌های کاربری ({users.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('departments')}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              activeTab === 'departments'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:text-slate-900'
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>واحدها و گروه‌های سازمانی ({departments.length})</span>
          </button>
        </div>

      </div>

      {/* Tab 1: Users View */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          
          {/* User Search & Department Filter */}
          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-xs flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="جست‌وجو بر اساس نام، نام کاربری، ایمیل یا واحد..."
                className="w-full bg-slate-100 text-xs text-slate-800 pr-9 pl-4 py-2 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
              />
              <Search className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />
            </div>

            <select
              value={selectedDeptFilter}
              onChange={(e) => setSelectedDeptFilter(e.target.value)}
              className="bg-slate-100 text-xs text-slate-800 px-3 py-2 rounded-xl border border-slate-200 focus:border-blue-600 focus:outline-hidden"
            >
              <option value="all">همه واحدهای سازمانی</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          {/* Users Table */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-right text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-3.5 pr-5">نام و مشخصات کاربر</th>
                    <th className="p-3.5">نام کاربری</th>
                    <th className="p-3.5">نقش سیستمی</th>
                    <th className="p-3.5">واحد سازمانی</th>
                    <th className="p-3.5">وضعیت حساب</th>
                    <th className="p-3.5">آخرین ورود</th>
                    <th className="p-3.5 pl-5 text-center">عملیات</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredUsers.map((user) => {
                    const isCurrentUser = user.id === currentUser.id;
                    const isActive = user.status === 'active';

                    return (
                      <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                        <td className="p-3.5 pr-5">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shrink-0">
                              {user.fullName[0]}
                            </div>
                            <div>
                              <p className="font-bold text-slate-800 flex items-center gap-1.5">
                                <span>{user.fullName}</span>
                                {isCurrentUser && (
                                  <span className="text-[9px] bg-blue-600 text-white px-1.5 py-0.2 rounded font-normal">
                                    شما
                                  </span>
                                )}
                              </p>
                              <p className="text-[10px] text-slate-500">{user.email}</p>
                            </div>
                          </div>
                        </td>

                        <td className="p-3.5 font-mono text-slate-700 font-semibold">
                          {user.username}
                        </td>

                        <td className="p-3.5">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                            user.role === 'system_admin'
                              ? 'bg-slate-900 text-white'
                              : user.role === 'group_admin'
                              ? 'bg-blue-600 text-white'
                              : user.role === 'user'
                              ? 'bg-slate-100 text-slate-700'
                              : 'bg-amber-100 text-amber-800'
                          }`}>
                            {StorageService.getRoleTitle(user.role)}
                          </span>
                        </td>

                        <td className="p-3.5 text-slate-500">
                          {user.departmentName}
                        </td>

                        <td className="p-3.5">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 w-fit ${
                            isActive ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'
                          }`}>
                            {isActive ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                            <span>{isActive ? 'فعال' : 'معلق / غیرفعال'}</span>
                          </span>
                        </td>

                        <td className="p-3.5 text-[11px] text-slate-500 font-mono whitespace-nowrap">
                          {user.lastLogin}
                        </td>

                        <td className="p-3.5 pl-5 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            
                            {/* Reset Password */}
                            <button
                              onClick={() => setShowResetPassModal(user)}
                              className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                              title="بازنشانی رمز عبور"
                            >
                              <KeyRound className="w-4 h-4" />
                            </button>

                            {/* Toggle active / suspended */}
                            {!isCurrentUser && (
                              <button
                                onClick={() => handleToggleUserStatus(user)}
                                className={`p-1.5 rounded-lg transition-colors ${
                                  isActive 
                                    ? 'text-amber-600 hover:bg-amber-50' 
                                    : 'text-emerald-600 hover:bg-emerald-50'
                                }`}
                                title={isActive ? 'تعلیق حساب' : 'فعال‌سازی حساب'}
                              >
                                {isActive ? <XCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                              </button>
                            )}

                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* Tab 2: Departments View */}
      {activeTab === 'departments' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {departments.map((dept) => {
            const memberCount = users.filter(u => u.departmentId === dept.id).length;

            return (
              <div
                key={dept.id}
                className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4 hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center font-bold text-sm">
                      <Building2 className="w-5 h-5" />
                    </div>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded border border-slate-200">
                      کد: {dept.code}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-bold text-sm text-slate-800">{dept.name}</h3>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">{dept.description}</p>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-500">
                      <span>مدیر مسئول واحد:</span>
                      <strong className="text-slate-900">{dept.managerName}</strong>
                    </div>
                    <div className="flex justify-between text-slate-500">
                      <span>تعداد پرسنل عضو:</span>
                      <strong className="text-slate-900 font-mono">{memberCount} نفر</strong>
                    </div>
                    <div className="flex justify-between text-slate-500">
                      <span>سقف مجاز بارگذاری:</span>
                      <strong className="text-blue-700 font-mono">{dept.maxFileSizeMB} مگابایت</strong>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500">
                  <span className="font-medium block mb-1">فرمت‌های مجاز:</span>
                  <div className="flex flex-wrap gap-1">
                    {(dept.allowedFileExtensions || []).map(ext => (
                      <span key={ext} className="bg-slate-100 text-slate-700 border border-slate-200 px-1.5 py-0.2 rounded uppercase font-mono text-[10px]">
                        .{ext}
                      </span>
                    ))}
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-blue-600" />
                <span>تعریف حساب کاربری جدید</span>
              </h2>
              <button onClick={() => setShowAddUserModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-600 mb-1">نام و نام خانوادگی:</label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="مثال: بهرام صادقی"
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden text-slate-800"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-600 mb-1">نام کاربری لاتین (Login Username):</label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="مثال: b.sadeghi"
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden font-mono text-slate-800"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium text-slate-600 mb-1">نقش دسترسی:</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as UserRole)}
                    className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:outline-hidden text-slate-800"
                  >
                    <option value="user">کاربر عادی</option>
                    <option value="group_admin">مدیر گروه</option>
                    <option value="system_admin">مدیر سامانه</option>
                    <option value="viewer">مشاهده‌گر</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-slate-600 mb-1">واحد سازمانی:</label>
                  <select
                    value={newDeptId}
                    onChange={(e) => setNewDeptId(e.target.value)}
                    className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:outline-hidden text-slate-800"
                  >
                    {departments.map(d => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-600 mb-1">ایمیل سازمانی:</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="b.sadeghi@eytan.local"
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden text-slate-800"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-600 mb-1">گذرواژه اولیه (حداقل ۱۲ نویسه):</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden text-slate-800"
                />
              </div>

              <div className="pt-2 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium"
                >
                  انصراف
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow-xs"
                >
                  ذخیره حساب کاربری
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Department Modal */}
      {showAddDeptModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FolderPlus className="w-4 h-4 text-blue-600" />
                <span>ایجاد واحد / گروه سازمانی جدید</span>
              </h2>
              <button onClick={() => setShowAddDeptModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateDepartment} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-600 mb-1">نام واحد سازمانی:</label>
                <input
                  type="text"
                  required
                  value={newDeptName}
                  onChange={(e) => setNewDeptName(e.target.value)}
                  placeholder="مثال: واحد حقوقی و قراردادها"
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden text-slate-800"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium text-slate-600 mb-1">کد اختصاری:</label>
                  <input
                    type="text"
                    required
                    value={newDeptCode}
                    onChange={(e) => setNewDeptCode(e.target.value)}
                    placeholder="مثال: LEGAL"
                    className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden font-mono uppercase text-slate-800"
                  />
                </div>

                <div>
                  <label className="block font-medium text-slate-600 mb-1">سقف حجم فایل (MB):</label>
                  <input
                    type="number"
                    value={newDeptMaxSize}
                    onChange={(e) => setNewDeptMaxSize(Number(e.target.value))}
                    min={1}
                    max={200}
                    className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden font-mono text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-600 mb-1">نام مدیر واحد:</label>
                <input
                  type="text"
                  value={newDeptManager}
                  onChange={(e) => setNewDeptManager(e.target.value)}
                  placeholder="مثال: حمید کریمی"
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden text-slate-800"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-600 mb-1">توضیحات و رسالت گروه:</label>
                <textarea
                  rows={2}
                  value={newDeptDesc}
                  onChange={(e) => setNewDeptDesc(e.target.value)}
                  placeholder="شرح کوتاه مسئولیت‌های واحد..."
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden resize-none text-slate-800"
                />
              </div>

              <div className="pt-2 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddDeptModal(false)}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium"
                >
                  انصراف
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow-xs"
                >
                  افزودن واحد
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPassModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-sm w-full border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-amber-600" />
                <span>بازنشانی رمز عبور کاربر</span>
              </h2>
              <button onClick={() => setShowResetPassModal(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleResetPassword} className="space-y-3 text-xs">
              <p className="text-slate-600">
                کاربر: <strong className="text-slate-900">{showResetPassModal.fullName}</strong> ({showResetPassModal.username})
              </p>

              <div>
                <label className="block font-medium text-slate-600 mb-1">کلمه عبور جدید (Argon2):</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="حداقل ۸ کاراکتر..."
                  className="w-full bg-slate-100 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden text-slate-800"
                />
              </div>

              <div className="pt-2 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowResetPassModal(null)}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium"
                >
                  انصراف
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow-xs"
                >
                  ثبت رمز عبور جدید
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
