import { AuditLog, Department, FileItem, SystemSecurityPolicy, User } from '../types';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function readCookie(name: string): string {
  const parts = document.cookie.split(';');
  for (const part of parts) {
    const [k, ...rest] = part.trim().split('=');
    if (k === name) return decodeURIComponent(rest.join('='));
  }
  return '';
}

export function csrfToken(): string {
  return readCookie('eytan_csrf');
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    return 'خطای سامانه';
  } catch {
    return 'خطای سامانه';
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const csrf = readCookie('eytan_csrf');
  if (csrf) headers.set('X-CSRF-Token', csrf);
  if (!(init.body instanceof FormData) && init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(path, {
    ...init,
    headers,
    credentials: 'include',
  });
  if (res.status === 401 && !path.includes('/api/auth/login')) {
    throw new ApiError(401, 'نشست منقضی شده است.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  if (res.status === 204) return {} as T;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return res.json();
  return {} as T;
}

export function mapUser(raw: any): User {
  return {
    id: raw.id,
    username: raw.username,
    fullName: raw.full_name,
    email: raw.email,
    role: raw.role,
    orgRoleId: raw.org_role_id,
    orgRoleName: raw.org_role_name,
    departmentId: raw.department_id || raw.group_id || '',
    departmentName: raw.department_name || '',
    status: raw.status,
    lastLogin: raw.last_login || '',
    createdAt: raw.created_at,
    phoneNumber: raw.phone_number,
    mustChangePassword: raw.must_change_password,
  };
}

export function mapGroup(raw: any): Department {
  return {
    id: raw.id,
    name: raw.name,
    code: raw.code,
    description: raw.description,
    managerId: raw.manager_id,
    managerName: raw.manager_name,
    membersCount: raw.members_count,
    allowedFileExtensions: raw.allowed_file_extensions || [],
    maxFileSizeMB: raw.max_file_size_mb,
    defaultClassification: raw.default_classification,
  };
}

export function mapFile(raw: any): FileItem {
  return {
    id: raw.id,
    title: raw.title,
    originalName: raw.original_name,
    storedVaultName: raw.stored_vault_name,
    topic: raw.topic,
    departmentId: raw.department_id || '',
    departmentName: raw.department_name || '',
    uploaderId: raw.uploader_id,
    uploaderName: raw.uploader_name,
    sizeBytes: raw.size_bytes,
    mimeType: raw.mime_type,
    extension: raw.extension,
    version: raw.version,
    classification: raw.classification,
    scanStatus: raw.scan_status,
    quarantineReason: raw.quarantine_reason,
    downloadCount: raw.download_count,
    viewCount: raw.view_count,
    tags: raw.tags || [],
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
    checksumSha256: raw.checksum_sha256,
    description: raw.description,
    canDownload: raw.can_download,
    canManage: raw.can_manage,
    versions: raw.versions,
    permissions: raw.permissions || [],
  };
}

export function mapLog(raw: any): AuditLog {
  return {
    id: raw.id,
    timestamp: raw.timestamp,
    userId: raw.user_id || '',
    username: raw.username,
    userRole: raw.user_role,
    action: raw.action,
    actionTitle: raw.action_title,
    targetResource: raw.target_resource,
    details: raw.details,
    ipAddress: raw.ip_address,
    userAgent: raw.user_agent,
    severity: raw.severity,
  };
}

export function mapPolicy(raw: any): SystemSecurityPolicy {
  return {
    allowedExtensions: raw.allowed_extensions || [],
    maxFileSizeBytes: raw.max_file_size_bytes,
    clamAvScanEnabled: raw.clamav_scan_enabled,
    quarantineDangerousFiles: raw.quarantine_dangerous_files,
    sessionTimeoutMinutes: raw.session_timeout_minutes,
    maxFailedLoginAttempts: raw.max_failed_login_attempts,
    lockoutDurationMinutes: raw.lockout_duration_minutes,
    passwordMinLength: raw.password_min_length,
    requireSpecialChars: raw.require_special_chars,
    vaultStoragePath: raw.vault_storage_path,
    enforceHttps: raw.enforce_https,
    allowDirectPathAccess: false,
  };
}

export function mapRole(raw: any): import('../types').OrgRole {
  return {
    id: raw.id,
    code: raw.code,
    name: raw.name,
    description: raw.description,
    permissionLevel: raw.permission_level,
    isSystem: raw.is_system,
    isActive: raw.is_active,
    membersCount: raw.members_count,
  };
}

export const AuthApi = {
  me: () => api<{ user: any; csrf_token: string; maintenance: boolean }>('/api/auth/me'),
  login: (username: string, password: string) =>
    api<{ user: any; csrf_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => api('/api/auth/logout', { method: 'POST' }),
  recoveryRequest: (username: string) =>
    api('/api/auth/recovery/request', { method: 'POST', body: JSON.stringify({ username }) }),
  recoveryConfirm: (token: string, new_password: string) =>
    api('/api/auth/recovery/confirm', { method: 'POST', body: JSON.stringify({ token, new_password }) }),
  changePassword: (current_password: string, new_password: string) =>
    api('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),
};

export const DataApi = {
  users: () => api<{ users: any[] }>('/api/users'),
  createUser: (payload: object) => api('/api/users', { method: 'POST', body: JSON.stringify(payload) }),
  patchUser: (id: string, payload: object) =>
    api(`/api/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  resetPassword: (id: string, new_password: string) =>
    api(`/api/users/${id}/reset-password`, { method: 'POST', body: JSON.stringify({ new_password }) }),
  groups: () => api<{ groups: any[] }>('/api/groups'),
  createGroup: (payload: object) => api('/api/groups', { method: 'POST', body: JSON.stringify(payload) }),
  patchGroup: (id: string, payload: object) =>
    api(`/api/groups/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteGroup: (id: string) => api(`/api/groups/${id}`, { method: 'DELETE' }),
  deleteUser: (id: string) => api(`/api/users/${id}`, { method: 'DELETE' }),
  roles: () => api<{ roles: any[] }>('/api/roles'),
  createRole: (payload: object) => api('/api/roles', { method: 'POST', body: JSON.stringify(payload) }),
  patchRole: (id: string, payload: object) =>
    api(`/api/roles/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteRole: (id: string) => api(`/api/roles/${id}`, { method: 'DELETE' }),
  files: (q = '') => api<{ files: any[] }>(`/api/files?q=${encodeURIComponent(q)}`),
  file: (id: string) => api<{ file: any }>(`/api/files/${id}`),
  patchFile: (id: string, payload: object) =>
    api(`/api/files/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteFile: (id: string) => api(`/api/files/${id}`, { method: 'DELETE' }),
  aiChat: (payload: object) => api<{ response: string; source?: string }>('/api/ai/chat', { method: 'POST', body: JSON.stringify(payload) }),
  aiSummarize: (payload: object) =>
    api<{ summary: string; source?: string }>('/api/ai/summarize', { method: 'POST', body: JSON.stringify(payload) }),
  logs: () => api<{ logs: any[] }>('/api/logs'),
  policy: () => api<{ policy: any }>('/api/settings/policy'),
  savePolicy: (payload: object) =>
    api('/api/settings/policy', { method: 'PUT', body: JSON.stringify(payload) }),
  infrastructure: () => api<{ infrastructure: any }>('/api/settings/infrastructure'),
  aiPrompts: () => api<{ prompts: { chat_prompt: string; summarize_prompt: string } }>('/api/settings/ai-prompts'),
  saveAiPrompts: (payload: object) =>
    api('/api/settings/ai-prompts', { method: 'PUT', body: JSON.stringify(payload) }),
  dashboard: (range = 'week') => api<any>(`/api/dashboard?range=${range}`),
  updates: () => api<any>('/api/updates'),
  confirmUpdate: (id: string) => api(`/api/updates/${id}/confirm`, { method: 'POST' }),
};

export async function uploadFile(form: FormData) {
  return api<{ file: any }>('/api/files', { method: 'POST', body: form });
}

export async function downloadFile(id: string, filename: string) {
  const csrf = readCookie('eytan_csrf');
  const res = await fetch(`/api/files/${id}/download`, {
    credentials: 'include',
    headers: { 'X-CSRF-Token': csrf },
  });
  if (!res.ok) {
    throw new ApiError(res.status, 'دریافت فایل ممکن نیست.');
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function uploadUpdateBundle(file: File) {
  const form = new FormData();
  form.append('file', file);
  return api<{ update: any }>('/api/updates/upload', { method: 'POST', body: form });
}
