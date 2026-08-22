export type UserRole = 'system_admin' | 'group_admin' | 'user' | 'viewer';
export type UserStatus = 'active' | 'suspended' | 'pending';
export type LogSeverity = 'info' | 'warning' | 'critical';
export type FileClassification = 'public' | 'internal' | 'confidential' | 'secret';
export type ScanStatus = 'clean' | 'scanning' | 'quarantined' | 'suspicious';

export interface User {
  id: string;
  username: string;
  fullName: string;
  email: string;
  role: UserRole;
  departmentId: string;
  departmentName: string;
  status: UserStatus;
  lastLogin: string;
  createdAt: string;
  phoneNumber?: string;
  mustChangePassword?: boolean;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description: string;
  managerId?: string;
  managerName: string;
  membersCount: number;
  allowedFileTypes?: string[];
  allowedFileExtensions?: string[];
  maxFileSizeMB: number;
  defaultClassification?: FileClassification;
}

export interface FileItem {
  id: string;
  title: string;
  originalName: string;
  storedVaultName: string;
  topic: string;
  departmentId: string;
  departmentName: string;
  uploaderId: string;
  uploaderName: string;
  sizeBytes: number;
  mimeType: string;
  extension: string;
  version: string;
  classification: FileClassification;
  scanStatus: ScanStatus;
  quarantineReason?: string;
  downloadCount: number;
  viewCount: number;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  checksumSha256: string;
  description?: string;
  canDownload?: boolean;
  canManage?: boolean;
  versions?: Array<{ id: string; version: string; created_at: string; scan_status: string }>;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  username: string;
  userRole: UserRole;
  action: string;
  actionTitle: string;
  targetResource: string;
  details: string;
  ipAddress: string;
  userAgent?: string;
  severity: LogSeverity;
}

export interface SystemSecurityPolicy {
  allowedExtensions: string[];
  maxFileSizeBytes: number;
  clamAvScanEnabled?: boolean;
  quarantineDangerousFiles?: boolean;
  sessionTimeoutMinutes: number;
  maxFailedLoginAttempts?: number;
  lockoutDurationMinutes: number;
  passwordMinLength?: number;
  requireSpecialChars?: boolean;
  vaultStoragePath?: string;
  enforceHttps?: boolean;
  allowDirectPathAccess?: boolean;
}

export interface DashboardData {
  kpis: {
    users_total: number;
    users_active: number;
    views: number;
    downloads: number;
    files_total: number;
    quarantined: number;
  };
  top_topics: Array<{ topic: string; count: number }>;
  events: Array<{
    user: string;
    file: string;
    topic: string;
    action: string;
    action_title: string;
    timestamp: string;
  }>;
}

export interface SystemUpdateItem {
  id: string;
  version: string;
  compatible_from: string;
  changelog: string;
  status: string;
  uploaded_by: string;
  created_at: string;
  error: string;
  migration_id: string;
}
