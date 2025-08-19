import Hashids from 'hashids';

// 创建 hashids 实例（使用与后端相同的配置）
export const hashids = new Hashids('dev-hashids-salt-change-in-prod', 8);
