import { FileItem, User, UserRole } from '../types';

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '۰ بایت';
  const k = 1024;
  const sizes = ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = (bytes / Math.pow(k, i)).toFixed(1);
  return `${val} ${sizes[i]}`;
}

export function formatDateTimeFa(value?: string): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(d);
}

export function getRoleTitle(role: UserRole | string): string {
  switch (role) {
    case 'system_admin':
      return 'مدیر سامانه';
    case 'group_admin':
      return 'مدیر گروه';
    case 'user':
      return 'کاربر';
    case 'viewer':
      return 'مشاهده‌گر';
    default:
      return String(role);
  }
}

export class StorageService {
  static canUserViewFile(_user: User, _file: FileItem): boolean {
    return true;
  }

  static canUserDownloadFile(_user: User, file: FileItem): boolean {
    return Boolean(file.canDownload);
  }

  static canUserManageFile(_user: User, file: FileItem): boolean {
    return Boolean(file.canManage);
  }

  static canUserUpload(user: User): boolean {
    return user.role !== 'viewer' && user.status === 'active';
  }

  static canUserAccessAdmin(user: User): boolean {
    return user.role === 'system_admin' || user.role === 'group_admin';
  }

  static getRoleTitle(role: UserRole): string {
    return getRoleTitle(role);
  }
}
