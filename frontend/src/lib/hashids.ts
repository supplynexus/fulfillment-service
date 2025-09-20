import Hashids from 'hashids';

// 创建 hashids 实例（使用环境变量配置）
// 注意：生产环境必须设置正确的 HASHIDS_SALT 和 HASHIDS_MIN_LENGTH
const HASHIDS_SALT = process.env.NEXT_PUBLIC_HASHIDS_SALT || 'dev-hashids-salt-change-in-prod';
const HASHIDS_MIN_LENGTH = parseInt(process.env.NEXT_PUBLIC_HASHIDS_MIN_LENGTH || '8');

export const hashids = new Hashids(HASHIDS_SALT, HASHIDS_MIN_LENGTH);
