'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Chip,
  Grid,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface Variant {
  id?: string;
  id_hashid: string;
  sku: string;
  title?: string;
  name?: string;
  price: number;
  inventory_quantity?: number;
  option1?: string;
  option2?: string;
  option3?: string;
  /** Printify: option value IDs in same order as product.options */
  options?: number[];
  attributes?: Record<string, unknown>;
}

/** Printify 商品维度定义，与变体 options[] 顺序一致 */
interface PrintifyOption {
  name: string;
  type?: string;
  values?: Array<{ id: number; title: string }>;
}

interface VariantMappingDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (mappings: VariantMapping[]) => void;
  coreProduct: {
    id_hashid: string;
    title: string;
    variants: Variant[];
  };
  printifyProduct: {
    printify_product_id: string;
    title: string;
    variants: Variant[];
    /** 维度定义，用于按「维度名+取值」匹配变体（core 与 Printify 维度可名称不同，如 color ↔ Color） */
    options?: PrintifyOption[];
  };
  printifySystemId: string;
  /** 创建映射前校验的警告（标题/变体维度不一致等），若有则顶部展示 */
  validationWarnings?: string[];
}

interface VariantMapping {
  core_variant_id: string;
  external_variant_id: string;
  core_variant_sku: string;
  external_variant_sku: string;
  core_variant_title: string;
  external_variant_title: string;
}

export function VariantMappingDialog({
  open,
  onClose,
  onConfirm,
  coreProduct,
  printifyProduct,
  printifySystemId,
  validationWarnings,
}: VariantMappingDialogProps) {
  const [mappings, setMappings] = useState<VariantMapping[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 从变体 title/name/attributes/option1-3 生成显示标签，如 "Light Pink / S" */
  const getCoreVariantDisplayLabel = (variant: Variant): string => {
    if (variant.title != null && String(variant.title).trim()) return String(variant.title).trim();
    if (variant.name != null && String(variant.name).trim()) return String(variant.name).trim();
    const attrs = variant.attributes as Record<string, unknown> | undefined;
    if (attrs && typeof attrs === 'object') {
      const titleFromAttrs = attrs.title;
      if (titleFromAttrs != null && String(titleFromAttrs).trim()) return String(titleFromAttrs).trim();
      const parts = Object.entries(attrs)
        .filter(([k, v]) => k !== 'title' && v != null && v !== '')
        .map(([, v]) => String(v));
      if (parts.length > 0) return parts.join(' / ');
    }
    const options = [variant.option1, variant.option2, variant.option3]
      .filter((v): v is string => v != null && String(v).trim() !== '');
    if (options.length > 0) return options.join(' / ');
    return variant.sku || '—';
  };

  // --- 维度映射：核心维度名 → Printify 维度名（case-insensitive，如 color ↔ Color）---
  const printifyOpts = printifyProduct.options || [];
  const coreDimToPrintifyDim = React.useMemo(() => {
    const coreNames = new Set<string>();
    coreProduct.variants?.forEach(v => {
      const attrs = (v as Variant).attributes as Record<string, unknown> | undefined;
      if (attrs && typeof attrs === 'object') {
        Object.keys(attrs).forEach(k => {
          if ((k || '').toLowerCase() !== 'title' && (k || '').toLowerCase() !== 'name') coreNames.add(k);
        });
      }
    });
    /** 维度名等价（Color ↔ Colors, Size ↔ Sizes） */
    const dimNamesMatch = (a: string, b: string) => {
      const x = (a || '').toLowerCase().trim();
      const y = (b || '').toLowerCase().trim();
      return x === y || x + 's' === y || y + 's' === x;
    };
    const map: Record<string, string> = {};
    for (const cDim of coreNames) {
      const pOpt = printifyOpts.find((o: PrintifyOption) => dimNamesMatch(o.name || '', cDim || ''));
      if (pOpt?.name) map[cDim] = pOpt.name;
    }
    return map;
  }, [coreProduct.variants, printifyProduct.options]);

  /** 按「维度名:取值」生成唯一签名（按维度名排序；取值归一化为小写，避免 Core "White" 与 Printify "white" 不匹配） */
  const dimensionKeyToSignature = (key: Record<string, string>): string =>
    Object.entries(key)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}:${(v || '').trim().toLowerCase()}`)
      .filter(([, v]) => v !== '')
      .join('\t');

  /** 核心变体 → 以 Printify 维度名为 key 的取值对象（用于与 Printify 变体按维度对齐匹配） */
  const getCoreVariantDimensionKey = (variant: Variant): Record<string, string> | null => {
    const attrs = variant.attributes as Record<string, unknown> | undefined;
    if (!attrs || typeof attrs !== 'object') return null;
    const key: Record<string, string> = {};
    for (const [k, v] of Object.entries(attrs)) {
      const coreKey = (k || '').trim();
      if (!coreKey || ['title', 'name'].includes(coreKey.toLowerCase())) continue;
      const pDim = coreDimToPrintifyDim[coreKey];
      if (pDim != null && v != null && v !== '') key[pDim] = String(v).trim();
    }
    return Object.keys(key).length > 0 ? key : null;
  };

  /** Printify 变体 → 维度名到取值的对象（用 product.options + variant.options 解码） */
  const getPrintifyVariantDimensionKey = (variant: Variant): Record<string, string> | null => {
    const optIds = (variant as Variant & { options?: number[] }).options;
    if (!printifyOpts.length || !optIds || !Array.isArray(optIds)) return null;
    const key: Record<string, string> = {};
    printifyOpts.forEach((opt, i) => {
      const valId = optIds[i];
      if (valId == null) return;
      const val = opt.values?.find(v => Number(v.id) === Number(valId));
      if (val?.title != null) key[opt.name] = String(val.title).trim();
    });
    return Object.keys(key).length > 0 ? key : null;
  };

  /** 核心变体匹配用签名：优先按维度（维度名+取值），否则退化为取值排序（与 Printify 标题顺序无关） */
  const getCoreVariantMatchSignature = (variant: Variant): string => {
    const dimKey = getCoreVariantDimensionKey(variant);
    if (dimKey != null) return dimensionKeyToSignature(dimKey);
    const attrs = variant.attributes as Record<string, unknown> | undefined;
    if (attrs && typeof attrs === 'object') {
      const parts = Object.entries(attrs)
        .filter(([k, v]) => (k || '').toLowerCase() !== 'title' && v != null && v !== '')
        .map(([, v]) => String(v).trim())
        .filter(Boolean);
      if (parts.length > 0) return parts.slice().sort().join('\t');
    }
    const options = [variant.option1, variant.option2, variant.option3]
      .filter((v): v is string => v != null && String(v).trim() !== '')
      .map(s => s.trim());
    if (options.length > 0) return options.slice().sort().join('\t');
    if (variant.title != null && String(variant.title).trim()) {
      return String(variant.title)
        .split(/\s*\/\s*/)
        .map(s => s.trim())
        .filter(Boolean)
        .sort()
        .join('\t');
    }
    return '';
  };

  /** Printify 变体匹配用签名：优先按 product.options 解码的维度键；若为 null（如 White 变体 options 未解析），用标题按 option 顺序解析为「维度:取值」再生成签名，与 Core 一致 */
  const getPrintifyVariantMatchSignature = (variant: Variant): string => {
    const dimKey = getPrintifyVariantDimensionKey(variant);
    if (dimKey != null) return dimensionKeyToSignature(dimKey);
    const raw = (variant.title ?? variant.name ?? '').toString().trim();
    if (!raw) return '';
    const parts = raw.split(/\s*\/\s*/).map(s => s.trim()).filter(Boolean);
    if (parts.length === 0) return '';
    // 有 product.options 时，按 option 顺序把 title 各部分当作各维度取值，生成与 Core 同格式的 sig（Colors:white\tSizes:s）
    if (printifyOpts.length >= 1 && parts.length >= 1) {
      const syntheticKey: Record<string, string> = {};
      printifyOpts.forEach((opt, i) => {
        if (parts[i] != null) syntheticKey[opt.name] = parts[i];
      });
      if (Object.keys(syntheticKey).length > 0) return dimensionKeyToSignature(syntheticKey);
    }
    return parts.slice().sort().join('\t');
  };

  // 初始化映射，并按维度自动匹配（核心与 Printify 维度名可不同，按「维度名+取值」对齐）
  useEffect(() => {
    if (open && coreProduct.variants && printifyProduct.variants) {
      // --- 调试：Printify 维度定义与各变体签名（通过 frontendLogger 发送到 /api/log，在 Next 终端可见）---
      const printifyOpts = printifyProduct.options || [];
      frontendLogger.info('[VariantMapping] Printify product.options (dimension definitions)', {
        options: printifyOpts.map((o: PrintifyOption) => ({ name: o.name, values: o.values?.map(v => ({ id: v.id, title: v.title })) })),
      });
      frontendLogger.info('[VariantMapping] coreDimToPrintifyDim (core -> Printify dimension name)', coreDimToPrintifyDim);
      const printifySigs: { id: string; title: string; dimKey: Record<string, string> | null; sig: string }[] = printifyProduct.variants.map(pv => {
        const v = pv as Variant;
        const dimKey = getPrintifyVariantDimensionKey(v);
        const sig = getPrintifyVariantMatchSignature(v);
        return { id: String(pv.id), title: (pv.title ?? pv.name ?? '').toString(), dimKey, sig };
      });
      frontendLogger.info('[VariantMapping] Printify variant signatures (first 10 and unique sigs)', {
        first10: printifySigs.slice(0, 10),
        uniqueSigs: [...new Set(printifySigs.map(p => p.sig))],
      });
      const coreSigsSample = coreProduct.variants.slice(0, 8).map((v) => {
        const dimKey = getCoreVariantDimensionKey(v as Variant);
        const sig = getCoreVariantMatchSignature(v as Variant);
        return { label: getCoreVariantDisplayLabel(v as Variant), dimKey, sig };
      });
      frontendLogger.info('[VariantMapping] Core variant signatures (first 8, 含 S/White 等)', { coreSigsSample });

      const usedPrintifyIds = new Set<string>();
      const initialMappings: VariantMapping[] = coreProduct.variants.map(
        (coreVariant, index) => {
          const variantId = (coreVariant as Variant & { id?: string }).id ?? coreVariant.id_hashid ?? `variant-${index}`;
          const coreLabel = getCoreVariantDisplayLabel(coreVariant as Variant);
          const coreDimKey = getCoreVariantDimensionKey(coreVariant as Variant);
          const sig = getCoreVariantMatchSignature(coreVariant as Variant);
          const matched =
            sig &&
            printifyProduct.variants.find(
              pv =>
                getPrintifyVariantMatchSignature(pv as Variant) === sig &&
                !usedPrintifyIds.has(String(pv.id))
            );
          if (!matched && sig) {
            frontendLogger.warn('[VariantMapping] 未匹配到 Printify 变体', {
              coreLabel,
              coreDimKey,
              coreSig: sig,
              coreAttributes: (coreVariant as Variant).attributes,
              hint: '期望的 Printify 签名应与 coreSig 完全一致（含小写归一化）。检查 Printify 侧 option values 的 title 是否与 Core 一致（如 White vs 白色）。',
            });
          } else if (!sig) {
            frontendLogger.warn('[VariantMapping] 核心变体无签名，无法按维度匹配', { coreLabel, coreAttributes: (coreVariant as Variant).attributes });
          }
          if (matched) {
            usedPrintifyIds.add(String(matched.id));
          }
          return {
            core_variant_id: String(variantId),
            external_variant_id: matched ? String(matched.id) : '',
            core_variant_sku: coreVariant.sku ?? '',
            external_variant_sku: matched?.sku ?? '',
            core_variant_title: coreLabel,
            external_variant_title: matched?.title ?? '',
          };
        }
      );
      setMappings(initialMappings);
    }
  }, [open, coreProduct, printifyProduct]);

  /** 一键按维度匹配：对尚未映射的核心变体，按「维度名+取值」与 Printify 变体自动配对（不覆盖已选） */
  const handleAutoMatchByDimensions = () => {
    const usedPrintifyIds = new Set(
      mappings.filter(m => m.external_variant_id).map(m => m.external_variant_id!)
    );
    setMappings(prev =>
      prev.map(m => {
        if (m.external_variant_id) return m;
        const coreVariant = coreProduct.variants.find(
          v =>
            String((v as Variant & { id?: string }).id ?? v.id_hashid) === m.core_variant_id
        );
        if (!coreVariant) return m;
        const sig = getCoreVariantMatchSignature(coreVariant as Variant);
        if (!sig) return m;
        const matched = printifyProduct.variants.find(
          pv =>
            getPrintifyVariantMatchSignature(pv as Variant) === sig &&
            !usedPrintifyIds.has(String(pv.id))
        );
        if (matched) {
          usedPrintifyIds.add(String(matched.id));
          return {
            ...m,
            external_variant_id: String(matched.id),
            external_variant_sku: matched.sku ?? '',
            external_variant_title: matched.title ?? '',
          };
        }
        return m;
      })
    );
  };

  const handleVariantMappingChange = (
    coreVariantId: string,
    externalVariantId: string
  ) => {
    frontendLogger.info('[VariantMapping] 变体映射变化', { coreVariantId, externalVariantId });

    const externalVariant = printifyProduct.variants.find(
      v => String(v.id) === String(externalVariantId)
    );

    setMappings(prev => {
      const newMappings = prev.map(mapping =>
        mapping.core_variant_id === coreVariantId
          ? {
              ...mapping,
              external_variant_id: externalVariantId,
              external_variant_sku: externalVariant?.sku || '',
              external_variant_title: externalVariant?.title || '',
            }
          : mapping
      );
      frontendLogger.info('[VariantMapping] 新的映射状态', { count: newMappings.length, newMappings });
      return newMappings;
    });
  };

  const handleConfirm = async () => {
    try {
      setLoading(true);
      setError(null);

      // 检查是否所有变体都已映射
      const unmappedVariants = mappings.filter(m => !m.external_variant_id);
      if (unmappedVariants.length > 0) {
        setError(`还有 ${unmappedVariants.length} 个变体未映射`);
        return;
      }

      // 检查是否有重复映射
      const mappedExternalIds = mappings.map(m => m.external_variant_id);
      const uniqueExternalIds = new Set(mappedExternalIds);
      if (mappedExternalIds.length !== uniqueExternalIds.size) {
        setError('存在重复的 Printify 变体映射');
        return;
      }

      frontendLogger.info('🔗 开始创建变体映射', {
        coreProduct: coreProduct.title,
        printifyProduct: printifyProduct.title,
        mappingCount: mappings.length,
      });

      // 创建变体映射
      const createPromises = mappings.map(async (mapping, index) => {
        // 找到对应的核心商品变体，获取其真正的 hashid
        const coreVariant = coreProduct.variants[index];

        frontendLogger.info('[VariantMapping] 创建映射数据', {
          coreVariantHashid: coreVariant.id_hashid,
          coreVariantId: coreVariant.id,
          mapping: { core_variant_id: mapping.core_variant_id, external_variant_id: mapping.external_variant_id },
          mappingData: {
            core_product_id_hashid: coreProduct.id_hashid,
            core_variant_id_hashid: coreVariant.id_hashid || coreVariant.id,
            external_system_id_hashid: printifySystemId,
            external_product_id: printifyProduct.printify_product_id,
            external_variant_id: mapping.external_variant_id?.toString(),
            mapping_type: 'manual',
            sync_direction: 'bidirectional',
            sync_status: 'active',
          },
        });

        const mappingData = {
          core_product_id_hashid: coreProduct.id_hashid,
          core_variant_id_hashid: coreVariant.id_hashid || coreVariant.id,
          external_system_id_hashid: printifySystemId,
          external_product_id: printifyProduct.printify_product_id,
          external_variant_id: mapping.external_variant_id?.toString(),
          mapping_type: 'manual',
          sync_direction: 'bidirectional',
          sync_status: 'active',
        };

        return frontendApi.post('/api/products/mappings/', mappingData);
      });

      await Promise.all(createPromises);

      frontendLogger.info('✅ 变体映射创建成功', {
        coreProduct: coreProduct.title,
        printifyProduct: printifyProduct.title,
        mappingCount: mappings.length,
      });

      onConfirm(mappings);
    } catch (error) {
      frontendLogger.error('❌ 变体映射创建失败', {
        error: String(error),
        coreProduct: coreProduct.title,
        printifyProduct: printifyProduct.title,
      });
      setError('变体映射创建失败');
    } finally {
      setLoading(false);
    }
  };

  const getAvailablePrintifyVariants = (
    coreVariantId: string,
    currentMappings: VariantMapping[]
  ) => {
    const currentMapping = currentMappings.find(
      m => m.core_variant_id === coreVariantId
    );
    const usedExternalIds = currentMappings
      .filter(m => m.core_variant_id !== coreVariantId && m.external_variant_id)
      .map(m => m.external_variant_id);

    const availableVariants = printifyProduct.variants.filter(
      v =>
        !usedExternalIds.includes(String(v.id)) ||
        String(v.id) === String(currentMapping?.external_variant_id)
    );

    // 不再每次渲染下拉都打 log，避免刷屏；匹配原因见弹窗打开时的 [VariantMapping] Printify variant signatures / 未匹配到 Printify 变体
    return availableVariants;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth='lg' fullWidth>
      <DialogTitle>
        变体映射 - {coreProduct.title} → {printifyProduct.title}
      </DialogTitle>

      <DialogContent>
        {validationWarnings && validationWarnings.length > 0 && (
          <Alert severity='warning' sx={{ mb: 2 }}>
            <Typography variant='subtitle2' gutterBottom>
              一致性校验：存在以下差异，请确认是否仍要建立映射。
            </Typography>
            <Box component='ul' sx={{ m: 0, pl: 2 }}>
              {validationWarnings.map((w, i) => (
                <li key={i}>
                  <Typography variant='body2'>{w}</Typography>
                </li>
              ))}
            </Box>
          </Alert>
        )}
        {error && (
          <Alert severity='error' sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {/* 核心商品变体 */}
          <Box sx={{ width: "100%" }} md={6}>
            <Card>
              <CardContent>
                <Typography variant='h6' gutterBottom>
                  核心商品变体 ({coreProduct.variants.length})
                </Typography>
                <TableContainer component={Paper} variant='outlined'>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>标题</TableCell>
                        <TableCell>价格</TableCell>
                        <TableCell>库存</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {coreProduct.variants.map((variant, index) => (
                        <TableRow key={`core-variant-${variant.id_hashid ?? variant.id}-${index}`}>
                          <TableCell>{variant.sku}</TableCell>
                          <TableCell>{getCoreVariantDisplayLabel(variant as Variant)}</TableCell>
                          <TableCell>${variant.price}</TableCell>
                          <TableCell>{variant.inventory_quantity ?? '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Box>

          {/* Printify 变体 */}
          <Box sx={{ width: "100%" }} md={6}>
            <Card>
              <CardContent>
                <Typography variant='h6' gutterBottom>
                  Printify 变体 ({printifyProduct.variants.length})
                </Typography>
                <TableContainer component={Paper} variant='outlined'>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>标题</TableCell>
                        <TableCell>价格</TableCell>
                        <TableCell>库存</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {printifyProduct.variants.map((variant, index) => (
                        <TableRow
                          key={`printify-variant-${variant.id}-${index}`}
                        >
                          <TableCell>{variant.sku}</TableCell>
                          <TableCell>{variant.title}</TableCell>
                          <TableCell>${variant.price}</TableCell>
                          <TableCell>{variant.inventory_quantity}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Box>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* 映射配置 */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1, mb: 1 }}>
            <Typography variant='h6'>
              变体映射配置
            </Typography>
            <Button
              variant='outlined'
              size='small'
              onClick={handleAutoMatchByDimensions}
              disabled={mappings.every(m => m.external_variant_id)}
            >
              一键按维度匹配
            </Button>
          </Box>
          <Typography variant='body2' color='text.secondary' sx={{ mb: 1 }}>
            核心商品与 Printify 均有维度管理（如 Size、Color）；维度名可不同（如 color ↔ Color），按「维度+取值」自动匹配变体，避免混乱。未匹配时可点「一键按维度匹配」或手动选择。
          </Typography>
          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>核心变体</TableCell>
                  <TableCell>Printify 变体</TableCell>
                  <TableCell>状态</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mappings.map((mapping, index) => {
                  const availableVariants = getAvailablePrintifyVariants(
                    mapping.core_variant_id,
                    mappings
                  );
                  const isMapped = !!mapping.external_variant_id;

                  return (
                    <TableRow
                      key={`mapping-${index}-${mapping.core_variant_sku}`}
                    >
                      <TableCell>
                        <Box>
                          <Typography variant='body2' fontWeight='medium'>
                            {mapping.core_variant_title || '—'}
                          </Typography>
                          <Typography variant='caption' color='text.secondary' display='block'>
                            SKU: {mapping.core_variant_sku || 'N/A'}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <FormControl fullWidth size='small'>
                          <Select
                            value={mapping.external_variant_id || ''}
                            onChange={e =>
                              handleVariantMappingChange(
                                mapping.core_variant_id,
                                e.target.value
                              )
                            }
                            displayEmpty
                          >
                            <MenuItem value=''>
                              <em>选择 Printify 变体</em>
                            </MenuItem>
                            {availableVariants.map(variant => (
                              <MenuItem key={variant.id} value={variant.id}>
                                <Box>
                                  <Typography variant='body2'>
                                    {variant.title}
                                  </Typography>
                                  <Typography
                                    variant='caption'
                                    color='text.secondary'
                                  >
                                    SKU: {variant.sku}
                                  </Typography>
                                </Box>
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </TableCell>
                      <TableCell>
                        {isMapped ? (
                          <Chip label='已映射' color='success' size='small' />
                        ) : (
                          <Chip label='未映射' color='default' size='small' />
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          取消
        </Button>
        <Button
          onClick={handleConfirm}
          variant='contained'
          disabled={loading || mappings.some(m => !m.external_variant_id)}
        >
          {loading ? <CircularProgress size={20} /> : '确认映射'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
