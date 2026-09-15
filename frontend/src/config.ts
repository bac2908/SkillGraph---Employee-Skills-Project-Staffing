import type { Field } from './components/ui';
import { label } from './components/ui';

export const options = (values: string[]) =>
  values.map((value) => ({ value, label: label(value) }));
export const employeeStatuses = ['AVAILABLE', 'ASSIGNED', 'UNAVAILABLE', 'ON_LEAVE'];
export const projectStatuses = ['PLANNING', 'ACTIVE', 'ON_HOLD', 'COMPLETED', 'CANCELLED'];
export type Resource = 'employees' | 'skills' | 'projects';
export interface Entity {
  name: string;
  [key: string]: unknown;
}
export const configs: Record<
  Resource,
  {
    singular: string;
    title: string;
    description: string;
    id: string;
    fields: Field[];
    filter?: string;
    statuses?: string[];
  }
> = {
  employees: {
    singular: 'nhân viên',
    title: 'Những con người tạo khác biệt.',
    description: 'Hiểu đội ngũ, phát triển kỹ năng và kết nối đúng cơ hội.',
    id: 'employee_id',
    filter: 'status',
    statuses: employeeStatuses,
    fields: [
      {
        name: 'employee_id',
        label: 'Mã nhân viên',
        pattern: 'EMP[0-9]{3,}',
        hint: 'Ví dụ: EMP009',
      },
      { name: 'name', label: 'Họ và tên', maxLength: 100 },
      { name: 'email', label: 'Email', type: 'email' },
      { name: 'title', label: 'Chức danh', maxLength: 100 },
      {
        name: 'seniority',
        label: 'Cấp bậc',
        type: 'select',
        options: options(['Intern', 'Junior', 'Middle', 'Senior', 'Lead', 'Principal']),
      },
      {
        name: 'status',
        label: 'Trạng thái',
        type: 'select',
        options: options(employeeStatuses),
        hint: 'Trạng thái do quản trị viên cập nhật; không phản ánh allocation còn lại.',
      },
      { name: 'location', label: 'Địa điểm', maxLength: 100 },
    ],
  },
  skills: {
    singular: 'kỹ năng',
    title: 'Năng lực hôm nay. Tiềm năng ngày mai.',
    description: 'Một danh mục kỹ năng chung cho toàn bộ tổ chức.',
    id: 'skill_id',
    filter: 'category',
    fields: [
      { name: 'skill_id', label: 'Mã kỹ năng', pattern: 'SK[0-9]{3,}', hint: 'Ví dụ: SK013' },
      { name: 'name', label: 'Tên kỹ năng', maxLength: 100 },
      { name: 'category', label: 'Nhóm kỹ năng', maxLength: 100 },
    ],
  },
  projects: {
    singular: 'dự án',
    title: 'Xây đội ngũ cho điều tiếp theo.',
    description: 'Từ yêu cầu kỹ năng đến đội ngũ sẵn sàng triển khai.',
    id: 'project_id',
    filter: 'status',
    statuses: projectStatuses,
    fields: [
      { name: 'project_id', label: 'Mã dự án', pattern: 'PROJ[0-9]{3,}', hint: 'Ví dụ: PROJ004' },
      { name: 'name', label: 'Tên dự án', maxLength: 150 },
      { name: 'description', label: 'Mô tả', type: 'textarea', maxLength: 2000 },
      { name: 'status', label: 'Trạng thái', type: 'select', options: options(projectStatuses) },
    ],
  },
};
