'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Avatar,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Badge,
  Stack,
  Divider,
  CardMedia,
  Pagination,
  Link,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  Link as LinkIcon,
  LinkOff as UnlinkIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Print as PrintifyIcon,
  Inventory as InventoryIcon,
  Storefront as StorefrontIcon,
  Sync as SyncIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { VariantMappingDialog } from './VariantMappingDialog';
import { BatchMappingDialog } from './BatchMappingDialog';

interface CoreProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
  created_at: string;
  variants: CoreVariant[];
  /** 是否有任一映射到 Printify（后端 include_mappings 时返回） */
  has_printify_mapping?: boolean;
}

interface CoreVariant {
  id_hashid: string;
  sku: string;
  name: string;
  price: number;
  is_active: boolean;
  is_available: boolean;
  attributes: Record<string, any>;
}

interface PrintifyProduct {
  id: number;
  id_hashid: string;
  tenant_id: number;
  external_system_id: number;
  printify_product_id: string;
  printify_shop_id?: string;
  title: string;
  description?: string;
  tags?: string[];
  visible: boolean;
  is_locked: boolean;
  /** 是否已发布到销售渠道，用于筛选与角标 */
  is_published?: boolean;
  external?: {
    id: string;
    handle: string;
    sku: string;
  };
  user_id?: number;
  print_provider_id?: number;
  options?: Array<{
    name: string;
    type: string;
    values: Array<{
      id: number;
      title: string;
    }>;
  }>;
  variants?: PrintifyVariant[];
  images?: Array<{
    src: string;
    variant_ids: number[];
    position: string;
    is_default: boolean;
  }>;
  print_areas?: Array<{
    variant_ids: number[];
    placeholders: Array<{
      position: string;
      images: Array<{
        id: string;
        name: string;
        type: string;
        url: string;
        position: string;
        x: number;
        y: number;
        scale: number;
        angle: number;
      }>;
    }>;
  }>;
  raw_data?: any;
  last_synced_at?: string;
  sync_status: string;
  sync_error?: string;
  created_at: string;
  updated_at?: string;
}

interface PrintifyVariant {
  id: number;
  sku: string;
  cost: number;
  price: number;
  title: string;
  grams: number;
  is_enabled: boolean;
  is_default: boolean;
  is_available: boolean;
  options: number[];
}

/** 创建映射前的校验结果：标题与变体维度是否一致或近似 */
interface MappingValidation {
  titleMatch: 'exact' | 'similar' | 'mismatch';
  titleMessage?: string;
  dimensionMatch: boolean;
  dimensionMessage?: string;
  variantCountCore: number;
  variantCountPrintify: number;
  variantCountMatch: boolean;
  warnings: string[];
  canForce: boolean;
}

function normalizeTitle(s: string): string {
  return (s || '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function computeMappingValidation(
  core: CoreProduct,
  printify: PrintifyProduct
): MappingValidation {
  const warnings: string[] = [];
  let titleMatch: 'exact' | 'similar' | 'mismatch' = 'exact';
  let titleMessage: string | undefined;
  let dimensionMatch = true;
  let dimensionMessage: string | undefined;

  const coreTitle = normalizeTitle(core.title);
  const printifyTitle = normalizeTitle(printify.title);
  if (coreTitle === printifyTitle) {
    titleMatch = 'exact';
  } else if (
    coreTitle && printifyTitle &&
    (coreTitle.includes(printifyTitle) || printifyTitle.includes(coreTitle))
  ) {
    titleMatch = 'similar';
    titleMessage = '标题不完全一致，但包含关系';
  } else {
    titleMatch = 'mismatch';
    titleMessage = '标题不一致';
    warnings.push('标题不一致，请确认是否为同一商品。');
  }

  const variantCountCore = core.variants?.length ?? 0;
  const variantCountPrintify = printify.variants?.length ?? 0;
  const variantCountMatch = variantCountCore === variantCountPrintify;
  if (!variantCountMatch) {
    warnings.push(
      `变体数量不一致：核心 ${variantCountCore} 个，Printify ${variantCountPrintify} 个。`
    );
  }

  // 核心商品维度：应以来源平台商品定义为准（如 Shopify 的 options → variant.selectedOptions 的 name）。
  // 若历史数据里误存了展示用字段（variant.title 等），此处排除，不参与维度比对。
  const DISPLAY_ONLY_ATTR_KEYS = new Set(['title', 'name']);
  const coreDimNames = new Set<string>();
  const coreDimValues: Record<string, Set<string>> = {};
  if (core.variants?.length) {
    for (const v of core.variants) {
      const attrs = v.attributes || {};
      for (const [k, val] of Object.entries(attrs)) {
        const key = (k || '').trim();
        if (!key || DISPLAY_ONLY_ATTR_KEYS.has(key.toLowerCase())) continue;
        coreDimNames.add(key);
        if (!coreDimValues[key]) coreDimValues[key] = new Set();
        coreDimValues[key].add(String(val).trim());
      }
    }
  }
  const coreDimList = Array.from(coreDimNames).sort();

  let printifyDimList: string[] = [];
  const printifyDimValues: Record<string, Set<string>> = {};
  const opts = printify.options || [];
  for (const opt of opts) {
    const name = (opt.name || '').trim();
    if (!name) continue;
    printifyDimList.push(name);
    const vals = new Set<string>();
    for (const v of opt.values || []) {
      const t = (v.title || '').trim();
      if (t) vals.add(t);
    }
    printifyDimValues[name] = vals;
  }
  printifyDimList = printifyDimList.sort();

  /** 维度名是否等价（含单复数：Color ↔ Colors, Size ↔ Sizes） */
  const dimensionNamesMatch = (a: string, b: string): boolean => {
    const x = (a || '').toLowerCase().trim();
    const y = (b || '').toLowerCase().trim();
    if (x === y) return true;
    if (x + 's' === y || y + 's' === x) return true;
    return false;
  };

  const coreDimSet = new Set(coreDimList.map(d => d.toLowerCase()));
  const printifyDimSet = new Set(printifyDimList.map(d => d.toLowerCase()));
  if (coreDimList.length !== printifyDimList.length || coreDimSet.size !== printifyDimSet.size) {
    dimensionMatch = false;
    dimensionMessage = `维度数量不一致：核心 [${coreDimList.join(', ') || '无'}], Printify [${printifyDimList.join(', ') || '无'}]`;
    warnings.push(dimensionMessage);
  } else {
    for (const cDim of coreDimList) {
      const pDim = printifyDimList.find(p => dimensionNamesMatch(p, cDim));
      if (!pDim) {
        dimensionMatch = false;
        dimensionMessage = `维度名称不一致：核心有「${cDim}」，Printify 无对应维度`;
        warnings.push(dimensionMessage);
        break;
      }
      const cVals = coreDimValues[cDim];
      const pVals = printifyDimValues[pDim];
      if (cVals && pVals) {
        const cArr = Array.from(cVals);
        const pArr = Array.from(pVals);
        const overlap = cArr.filter(x => pArr.some(y => y.toLowerCase() === x.toLowerCase())).length;
        if (overlap === 0 && (cArr.length > 0 || pArr.length > 0)) {
          dimensionMatch = false;
          dimensionMessage = `维度「${pDim}」取值无重叠：核心 [${cArr.slice(0, 5).join(', ')}${cArr.length > 5 ? '...' : ''}], Printify [${pArr.slice(0, 5).join(', ')}${pArr.length > 5 ? '...' : ''}]`;
          warnings.push(dimensionMessage);
        } else if (overlap < Math.min(cArr.length, pArr.length) * 0.5) {
          warnings.push(`维度「${pDim}」取值部分重叠，请核对是否同一规格体系。`);
        }
      }
    }
  }

  return {
    titleMatch,
    titleMessage,
    dimensionMatch,
    dimensionMessage,
    variantCountCore,
    variantCountPrintify,
    variantCountMatch,
    warnings,
    canForce: true,
  };
}

interface PrintifyStore {
  id_hashid: string;
  name: string;
  system_type: string;
  external_id?: string;
  is_active: boolean;
}

interface ProductMapping {
  id: string;
  id_hashid: string;
  core_product_id: number;
  core_variant_id: number | null;
  external_system_id: number;
  external_product_id: string;
  external_variant_id: string | null;
  mapping_type: string;
  sync_direction: string;
  sync_status: string;
  created_at: string;
  updated_at: string;
  core_product_title: string;
  core_variant_sku: string | null;
  external_system_name: string;
  system_type: string;
  printify_product_title: string;
  printify_variant_sku: string | null;
}

interface PrintifyMappingProps {
  /** 从订单详情等跳转时传入，预选该核心商品以便绑定 Printify */
  initialCoreProductIdHashid?: string;
}

export function PrintifyMapping({ initialCoreProductIdHashid }: PrintifyMappingProps = {}) {
  const [coreProducts, setCoreProducts] = useState<CoreProduct[]>([]);
  const [printifyProducts, setPrintifyProducts] = useState<PrintifyProduct[]>(
    []
  );
  const [printifyStores, setPrintifyStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(
    null
  );
  const [mappings, setMappings] = useState<ProductMapping[]>([]);
  const [selectedMappingIds, setSelectedMappingIds] = useState<string[]>([]);
  const mappingRowsPerPage = 10;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和筛选状态
  const [coreSearchTerm, setCoreSearchTerm] = useState('');
  const [printifySearchTerm, setPrintifySearchTerm] = useState('');
  const [selectedCoreProducts, setSelectedCoreProducts] = useState<string[]>(
    []
  );
  const [selectedPrintifyProducts, setSelectedPrintifyProducts] = useState<
    number[]
  >([]);

  // 映射对话框状态
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [mappingStatus, setMappingStatus] = useState<'active' | 'pending'>(
    'active'
  );
  const [mappingValidation, setMappingValidation] =
    useState<MappingValidation | null>(null);
  const [selectedCoreProduct, setSelectedCoreProduct] =
    useState<CoreProduct | null>(null);
  const [selectedPrintifyProduct, setSelectedPrintifyProduct] =
    useState<PrintifyProduct | null>(null);

  // 详情对话框状态
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState<ProductMapping | null>(
    null
  );

  // 变体映射对话框状态
  const [variantMappingDialogOpen, setVariantMappingDialogOpen] =
    useState(false);
  const [printifySystemId, setPrintifySystemId] = useState<string>('');

  // 批量映射对话框状态
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);

  // 同步状态
  const [syncing, setSyncing] = useState(false);

  // 分页状态
  const [corePage, setCorePage] = useState(1);
  const [printifyPage, setPrintifyPage] = useState(1);
  const [mappingListPage, setMappingListPage] = useState(1); // 仅用于「现有映射关系」表格翻页
  const [itemsPerPage] = useState(10);

  // 获取核心商品数据
  const fetchCoreProducts = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取核心商品列表');

      const response = await frontendApi.get('/api/products', {
        params: {
          page: corePage,
          limit: itemsPerPage,
          include_variants: true,
          include_dimensions: false,
          include_tags: false,
          include_mappings: true, // 用于「仅未映射到 Printify」筛选
        },
      });

      if (response.data && response.data.products) {
        setCoreProducts(response.data.products);
        frontendLogger.info('✅ 核心商品列表获取成功', {
          count: response.data.products.length,
        });
      } else {
        throw new Error('获取核心商品列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取核心商品列表失败', {
        error: String(error),
      });
      setError('获取核心商品列表失败');
    }
  }, [corePage, itemsPerPage]);

  // 获取 Printify 店铺列表
  const fetchPrintifyStores = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取 Printify 店铺列表');

      const response = await frontendApi.get('/api/external-systems', {
        params: { system_type: 'PRINTIFY' },
      });

      if (response.data && response.data.external_systems) {
        const printifyStores = response.data.external_systems.filter(
          (store: any) => store.system_type === 'PRINTIFY' && store.is_active
        );
        setPrintifyStores(printifyStores);
        frontendLogger.info('✅ Printify 店铺列表获取成功', {
          count: printifyStores.length,
        });

        // 如果有店铺，默认选择第一个
        if (printifyStores.length > 0) {
          setSelectedStore(printifyStores[0]);
          setPrintifySystemId(printifyStores[0].id_hashid);
        }
      } else {
        throw new Error('获取店铺列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 店铺列表失败', {
        error: String(error),
      });
      setError('获取店铺列表失败');
    }
  }, []);

  // 获取 Printify 商品数据（从本地数据库）；默认仅已发布，可选显示未发布
  const fetchPrintifyProducts = useCallback(
    async (store: PrintifyStore, publishedOnly: boolean = true) => {
      if (!store) return;

      try {
        frontendLogger.info('🔍 开始获取 Printify 商品列表（本地数据库）', {
          storeId: store.id_hashid,
          storeName: store.name,
          publishedOnly,
        });

        const response = await frontendApi.get('/api/printify-products/', {
          params: {
            external_system_id: store.id_hashid,
            limit: 100,
            offset: 0,
            visible_only: true,
            published_only: publishedOnly,
          },
        });

      if (response.data && response.data.products) {
        const productsData = response.data.products || [];
        setPrintifyProducts(productsData);
        frontendLogger.info('✅ Printify 商品列表获取成功（本地数据库）', {
          count: productsData.length,
          storeName: store.name,
        });
      } else {
        throw new Error('获取商品列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 商品列表失败（本地数据库）', {
        error: String(error),
        storeId: store.id_hashid,
      });
      setError('获取商品列表失败');
    }
  }, []);

  // 获取映射关系
  const fetchMappings = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取商品映射关系');

      const response = await frontendApi.get('/api/products/mappings/', {
        params: {
          page: 1,
          limit: 100,
          system_type: 'PRINTIFY',
        },
      });

      if (response.data && response.data.mappings) {
        setMappings(response.data.mappings);
        frontendLogger.info('✅ 商品映射关系获取成功', {
          count: response.data.mappings.length,
        });
      } else {
        throw new Error('获取映射关系失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取商品映射关系失败', {
        error: String(error),
      });
      setError('获取映射关系失败');
    }
  }, []);

  // 初始化数据
  const fetchSingleCoreProduct = useCallback(
    async (productHashid: string) => {
      const res = await frontendApi.get(`/api/products/${productHashid}`, {
        params: { include_variants: true, include_mappings: true },
      });
      const p = res.data;
      const coreProduct: CoreProduct = {
        id_hashid: p.id_hashid,
        title: p.title,
        vendor: p.vendor || '',
        product_type: p.product_type || '',
        status: p.status || '',
        is_active: p.is_active ?? true,
        is_available: p.is_available ?? true,
        created_at: p.created_at,
        variants: (p.variants || []).map((v: any) => ({
          id_hashid: v.id_hashid,
          sku: v.sku,
          name: v.name || v.sku,
          price: v.price ?? 0,
          is_active: v.is_active ?? true,
          is_available: v.is_available ?? true,
          attributes: v.attributes || {},
        })),
        has_printify_mapping: p.has_printify_mapping,
      };
      setCoreProducts([coreProduct]);
      setSelectedCoreProducts([productHashid]);
    },
    []
  );

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (initialCoreProductIdHashid) {
        await Promise.all([
          fetchSingleCoreProduct(initialCoreProductIdHashid),
          fetchPrintifyStores(),
          fetchMappings(),
        ]);
      } else {
        await Promise.all([
          fetchCoreProducts(),
          fetchPrintifyStores(),
          fetchMappings(),
        ]);
      }
    } catch (err: any) {
      frontendLogger.error('❌ 初始化数据失败', { error: err.message });
      setError(err.response?.data?.detail || err.message || '初始化数据失败');
    } finally {
      setLoading(false);
    }
  }, [
    initialCoreProductIdHashid,
    fetchSingleCoreProduct,
    fetchCoreProducts,
    fetchPrintifyStores,
    fetchMappings,
  ]);

  // 仅显示未映射的筛选（默认开启，便于补齐映射）
  const [showOnlyUnmappedCore, setShowOnlyUnmappedCore] = useState(true);
  const [showOnlyUnmappedPrintify, setShowOnlyUnmappedPrintify] = useState(true);
  // Printify 右侧列表：默认仅已发布（避免未发布/店铺不一致混入）
  const [printifyPublishedOnly, setPrintifyPublishedOnly] = useState(true);

  // 当选择店铺或「仅已发布」变更时重新获取 Printify 商品
  useEffect(() => {
    if (selectedStore) {
      fetchPrintifyProducts(selectedStore, printifyPublishedOnly);
    }
  }, [selectedStore, printifyPublishedOnly, fetchPrintifyProducts]);

  // 映射列表变化时，若当前页无数据则回到第 1 页
  useEffect(() => {
    const maxPage = Math.max(
      1,
      Math.ceil(mappings.length / mappingRowsPerPage)
    );
    if (mappingListPage > maxPage) {
      setMappingListPage(1);
    }
  }, [mappings.length, mappingListPage, mappingRowsPerPage]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 已映射到 Printify 的 external_product_id 集合（用于 Printify 列表筛选）
  const mappedPrintifyProductIds = new Set(
    mappings.map(m => m.external_product_id)
  );

  // 过滤商品：搜索 + 可选「仅未映射」
  const filteredCoreProducts = coreProducts
    .filter(
      product =>
        product.title.toLowerCase().includes(coreSearchTerm.toLowerCase()) ||
        (product.vendor || '').toLowerCase().includes(coreSearchTerm.toLowerCase())
    )
    .filter(
      product =>
        !showOnlyUnmappedCore || product.has_printify_mapping !== true
    );

  const filteredPrintifyProducts = printifyProducts
    .filter(
      product =>
        product.title.toLowerCase().includes(printifySearchTerm.toLowerCase()) ||
        (product.description &&
          product.description
            .toLowerCase()
            .includes(printifySearchTerm.toLowerCase())) ||
        (product.tags || []).some(tag =>
          tag.toLowerCase().includes(printifySearchTerm.toLowerCase())
        )
    )
    .filter(
      product =>
        !showOnlyUnmappedPrintify ||
        !mappedPrintifyProductIds.has(product.printify_product_id)
    );

  // 检查商品是否已映射
  const isProductMapped = (
    coreProductId: string,
    printifyProductId: string
  ) => {
    return mappings.some(
      mapping =>
        mapping.core_product_id.toString() === coreProductId &&
        mapping.external_product_id === printifyProductId
    );
  };

  // 选择商品
  const handleCoreProductSelect = (productId: string) => {
    setSelectedCoreProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  const handlePrintifyProductSelect = (productId: number) => {
    setSelectedPrintifyProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  // 创建映射
  const handleCreateMapping = () => {
    if (
      selectedCoreProducts.length === 0 ||
      selectedPrintifyProducts.length === 0
    ) {
      setError('请选择要映射的商品');
      return;
    }

    // 如果选择了多个商品，显示批量映射对话框
    if (
      selectedCoreProducts.length > 1 ||
      selectedPrintifyProducts.length > 1
    ) {
      setBatchDialogOpen(true);
    } else {
      const coreProduct = coreProducts.find(
        p => p.id_hashid === selectedCoreProducts[0]
      );
      const printifyProduct = printifyProducts.find(
        p => p.id === selectedPrintifyProducts[0]
      );

      if (coreProduct && printifyProduct) {
        setSelectedCoreProduct(coreProduct);
        setSelectedPrintifyProduct(printifyProduct);
        setMappingValidation(computeMappingValidation(coreProduct, printifyProduct));

        // 检查是否有变体，如果有则显示变体映射对话框
        if (
          coreProduct.variants &&
          coreProduct.variants.length > 0 &&
          printifyProduct.variants &&
          printifyProduct.variants.length > 0
        ) {
          frontendLogger.info('[VariantMapping] 打开变体映射弹窗（创建映射）', {
            coreTitle: coreProduct.title,
            printifyTitle: printifyProduct.title,
            coreVariantsCount: coreProduct.variants.length,
            printifyVariantsCount: printifyProduct.variants.length,
          });
          setVariantMappingDialogOpen(true);
        } else {
          setMappingDialogOpen(true);
        }
      }
    }
  };

  // 确认创建映射
  const handleConfirmMapping = async () => {
    if (!selectedCoreProduct || !selectedPrintifyProduct) return;

    try {
      frontendLogger.info('🔗 开始创建商品映射', {
        coreProduct: selectedCoreProduct.title,
        printifyProduct: selectedPrintifyProduct.title,
      });

      // 获取Printify外部系统ID
      const externalSystemsResponse = await frontendApi.get(
        '/api/external-systems',
        {
          params: { system_type: 'PRINTIFY' },
        }
      );

      const printifySystem = externalSystemsResponse.data.external_systems?.[0];
      if (!printifySystem) {
        throw new Error('未找到Printify外部系统配置');
      }

      const mappingData = {
        core_product_id_hashid: selectedCoreProduct.id_hashid,
        core_variant_id_hashid: null, // 暂时不映射变体
        external_system_id_hashid: printifySystem.id_hashid,
        external_product_id: selectedPrintifyProduct.printify_product_id,
        external_variant_id: null, // 暂时不映射变体
        mapping_type: 'manual',
        sync_direction: 'bidirectional',
        sync_status: mappingStatus,
      };

      // 调用后端API创建映射
      const response = await frontendApi.post(
        '/api/products/mappings/',
        mappingData
      );

      frontendLogger.info('✅ 商品映射创建成功', {
        coreProduct: selectedCoreProduct.title,
        printifyProduct: selectedPrintifyProduct.title,
      });

      // 刷新数据
      await fetchData();

      setMappingDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedPrintifyProducts([]);
      setSelectedCoreProduct(null);
      setSelectedPrintifyProduct(null);
    } catch (error) {
      frontendLogger.error('❌ 创建商品映射失败', {
        error: String(error),
      });
      setError('创建商品映射失败');
    }
  };

  // 确认变体映射
  const handleConfirmVariantMapping = async (mappings: any[]) => {
    try {
      frontendLogger.info('✅ 变体映射创建成功', {
        coreProduct: selectedCoreProduct?.title,
        printifyProduct: selectedPrintifyProduct?.title,
        mappingCount: mappings.length,
      });

      // 刷新数据
      await fetchData();

      setVariantMappingDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedPrintifyProducts([]);
      setSelectedCoreProduct(null);
      setSelectedPrintifyProduct(null);
    } catch (error) {
      frontendLogger.error('❌ 变体映射处理失败', {
        error: String(error),
      });
      setError('变体映射处理失败');
    }
  };

  // 删除映射
  const handleRemoveMapping = async (mappingId: string) => {
    try {
      frontendLogger.info('🗑️ 开始删除商品映射', { mappingId });

      await frontendApi.delete(`/api/products/mappings/${mappingId}`);

      frontendLogger.info('✅ 商品映射删除成功', { mappingId });

      setSelectedMappingIds(prev => prev.filter(id => id !== mappingId));
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 删除商品映射失败', {
        error: String(error),
        mappingId,
      });
      setError('删除商品映射失败');
    }
  };

  // 批量删除映射
  const handleRemoveMappings = async (ids: string[]) => {
    if (ids.length === 0) return;
    try {
      frontendLogger.info('🗑️ 开始批量删除商品映射', { count: ids.length });
      for (const id of ids) {
        await frontendApi.delete(`/api/products/mappings/${id}`);
      }
      frontendLogger.info('✅ 批量删除映射成功', { count: ids.length });
      setSelectedMappingIds([]);
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 批量删除映射失败', {
        error: String(error),
      });
      setError('批量删除映射失败');
    }
  };

  // 当前页的映射（用于全选）
  const currentPageMappings = mappings.slice(
    (mappingListPage - 1) * mappingRowsPerPage,
    (mappingListPage - 1) * mappingRowsPerPage + mappingRowsPerPage
  );
  const currentPageIds = currentPageMappings.map(m => m.id_hashid);
  const allCurrentPageSelected =
    currentPageIds.length > 0 &&
    currentPageIds.every(id => selectedMappingIds.includes(id));
  const someCurrentPageSelected = currentPageIds.some(id =>
    selectedMappingIds.includes(id)
  );

  const handleToggleSelectAllMappings = () => {
    if (allCurrentPageSelected) {
      setSelectedMappingIds(prev =>
        prev.filter(id => !currentPageIds.includes(id))
      );
    } else {
      setSelectedMappingIds(prev => [
        ...new Set([...prev, ...currentPageIds]),
      ]);
    }
  };

  const handleToggleSelectMapping = (idHashid: string) => {
    setSelectedMappingIds(prev =>
      prev.includes(idHashid)
        ? prev.filter(id => id !== idHashid)
        : [...prev, idHashid]
    );
  };

  // 查看映射详情
  const handleViewMappingDetail = (mapping: ProductMapping) => {
    setSelectedMapping(mapping);
    setDetailDialogOpen(true);
  };

  // 批量映射确认
  const handleBatchMappingConfirm = async (
    mappings: any[],
    status: 'active' | 'pending'
  ) => {
    try {
      frontendLogger.info('🔗 开始批量创建映射', {
        count: mappings.length,
        status,
      });

      // 刷新数据
      await fetchData();

      setBatchDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedPrintifyProducts([]);

      frontendLogger.info('✅ 批量映射创建成功', {
        count: mappings.length,
      });
    } catch (error) {
      frontendLogger.error('❌ 批量映射创建失败', {
        error: String(error),
      });
      setError('批量映射创建失败');
    }
  };

  // 批量映射取消
  const handleBatchMappingCancel = () => {
    setSelectedCoreProducts([]);
    setSelectedPrintifyProducts([]);
    setBatchDialogOpen(false);
  };

  // 更新映射状态
  const handleUpdateMappingStatus = async (
    mappingId: string,
    newStatus: string
  ) => {
    try {
      frontendLogger.info('🔄 开始更新映射状态', {
        mappingId,
        newStatus,
      });

      await frontendApi.patch(`/api/products/mappings/${mappingId}`, {
        sync_status: newStatus,
      });

      frontendLogger.info('✅ 映射状态更新成功', {
        mappingId,
        newStatus,
      });

      // 刷新数据
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 更新映射状态失败', {
        error: String(error),
        mappingId,
      });
      setError('更新映射状态失败');
    }
  };

  // 同步映射
  const handleSyncMapping = async (mappingId: string) => {
    try {
      frontendLogger.info('🔄 开始同步映射', { mappingId });

      await frontendApi.post(`/api/products/mappings/${mappingId}/sync`);

      frontendLogger.info('✅ 映射同步成功', { mappingId });

      // 刷新数据
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 映射同步失败', {
        error: String(error),
        mappingId,
      });
      setError('映射同步失败');
    }
  };

  // 清空该店铺下所有 Printify 本地数据（便于先删后重新同步）
  const [clearing, setClearing] = useState(false);
  const handleClearPrintifyProducts = async () => {
    if (!selectedStore) {
      setError('请先选择店铺');
      return;
    }
    if (!window.confirm('确定清空该店铺下所有 Printify 本地数据吗？清空后可再点击「同步商品到本地」重新拉取。')) return;
    try {
      setClearing(true);
      setError(null);
      await frontendApi.post('/api/printify-products/clear-by-external-system', {
        external_system_id_hashid: selectedStore.id_hashid,
      });
      frontendLogger.info('✅ 已清空 Printify 本地数据');
      await fetchPrintifyProducts(selectedStore);
    } catch (error) {
      frontendLogger.error('❌ 清空失败', { error: String(error) });
      setError('清空 Printify 数据失败');
    } finally {
      setClearing(false);
    }
  };

  // 同步后校验：查看 options/variants 摘要，确认数据是否正确
  const [verifyResult, setVerifyResult] = useState<Record<string, unknown> | null>(null);
  const handleVerifyData = async () => {
    if (!selectedStore) {
      setError('请先选择店铺');
      return;
    }
    try {
      setError(null);
      setVerifyResult(null);
      const res = await frontendApi.get(
        `/api/printify-products/verify-data?external_system_id_hashid=${encodeURIComponent(selectedStore.id_hashid)}&limit=2`
      );
      setVerifyResult(res.data);
      frontendLogger.info('校验数据结果', res.data);
    } catch (error) {
      frontendLogger.error('校验失败', { error: String(error) });
      setError('校验数据失败');
    }
  };

  // 同步 Printify 商品到本地数据库
  const handleSyncPrintifyProducts = async () => {
    if (!selectedStore) {
      setError('请先选择店铺');
      return;
    }

    try {
      setSyncing(true);
      setError(null);

      frontendLogger.info('🔄 开始同步 Printify 商品到本地数据库', {
        storeId: selectedStore.id_hashid,
        storeName: selectedStore.name,
      });

      const response = await frontendApi.post(
        '/api/printify-sync/sync-products',
        {
          external_system_id_hashid: selectedStore.id_hashid,
        }
      );

      frontendLogger.info('✅ Printify 商品同步成功', response.data);

      // 刷新商品列表
      await fetchPrintifyProducts(selectedStore);
    } catch (error) {
      frontendLogger.error('❌ Printify 商品同步失败', {
        error: String(error),
        storeId: selectedStore.id_hashid,
      });
      setError('同步 Printify 商品失败');
    } finally {
      setSyncing(false);
    }
  };


  // 获取商品主图
  const getProductImage = (product: PrintifyProduct) => {
    const defaultImage = product.images.find(img => img.is_default);
    return (
      defaultImage?.src || product.images[0]?.src || '/placeholder-product.png'
    );
  };

  // 获取商品价格范围（Printify API 返回分为单位，显示时除以 100 转为元）
  const getProductPriceRange = (product: PrintifyProduct) => {
    const prices = product.variants.map(v => v.price / 100).filter(p => p > 0);
    if (prices.length === 0) return 'N/A';
    if (prices.length === 1) return `$${prices[0].toFixed(2)}`;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max ? `$${min.toFixed(2)}` : `$${min.toFixed(2)} - $${max.toFixed(2)}`;
  };

  if (loading) {
    return (
      <Box
        display='flex'
        justifyContent='center'
        alignItems='center'
        minHeight='400px'
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Box display='flex' alignItems='center' gap={2}>
          <Avatar sx={{ bgcolor: '#96BF47' }}>
            <PrintifyIcon />
          </Avatar>
          <Typography variant='h4' component='h1'>
            Printify 商品映射
          </Typography>
        </Box>
        <Button
          variant='outlined'
          startIcon={<RefreshIcon />}
          onClick={fetchData}
          disabled={loading}
        >
          刷新数据
        </Button>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* 店铺选择 */}
      {printifyStores.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 2,
              }}
            >
              <Typography variant='h6'>选择 Printify 店铺</Typography>
              {selectedStore && (
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Button
                    variant='outlined'
                    startIcon={<SyncIcon />}
                    onClick={handleSyncPrintifyProducts}
                    disabled={syncing || clearing}
                    color='primary'
                  >
                    {syncing ? '同步中...' : '同步商品到本地'}
                  </Button>
                  <Button
                    variant='outlined'
                    onClick={handleClearPrintifyProducts}
                    disabled={syncing || clearing}
                    color='warning'
                  >
                    {clearing ? '清空中...' : '清空本地 Printify 数据'}
                  </Button>
                  <Button
                    variant='outlined'
                    onClick={handleVerifyData}
                    disabled={syncing || clearing}
                  >
                    校验数据（同步后查看）
                  </Button>
                </Box>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {printifyStores.map(store => (
                <Chip
                  key={store.id_hashid}
                  label={store.name}
                  color={
                    selectedStore?.id_hashid === store.id_hashid
                      ? 'primary'
                      : 'default'
                  }
                  onClick={() => setSelectedStore(store)}
                  variant={
                    selectedStore?.id_hashid === store.id_hashid
                      ? 'filled'
                      : 'outlined'
                  }
                />
              ))}
            </Box>
            {verifyResult && (
              <Alert
                severity='info'
                sx={{ mt: 2 }}
                onClose={() => setVerifyResult(null)}
              >
                <Typography variant='subtitle2' gutterBottom>
                  校验摘要（options 与变体样本）
                </Typography>
                <Box component='pre' sx={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', maxHeight: 320, overflow: 'auto' }}>
                  {JSON.stringify(verifyResult, null, 2)}
                </Box>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* 操作说明与筛选 */}
      <Alert severity='info' sx={{ mb: 2 }}>
        <strong>操作：</strong>左侧选核心商品、右侧选 Printify 商品，点击「创建映射」。本页仅关心核心↔Printify，不涉及 Shopify。勾选「仅未映射」可缩小范围，便于为每个核心商品找到对应 Printify。
      </Alert>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={showOnlyUnmappedCore}
              onChange={e => setShowOnlyUnmappedCore(e.target.checked)}
            />
          }
          label='仅显示未映射到 Printify 的核心商品'
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={showOnlyUnmappedPrintify}
              onChange={e => setShowOnlyUnmappedPrintify(e.target.checked)}
            />
          }
          label='仅显示未映射的 Printify 商品'
        />
      </Box>

      {/* 映射操作区域 */}
      {selectedCoreProducts.length > 0 &&
        selectedPrintifyProducts.length > 0 && (
          <Card
            sx={{
              mb: 3,
              bgcolor: 'primary.light',
              color: 'primary.contrastText',
            }}
          >
            <CardContent>
              <Box
                display='flex'
                justifyContent='space-between'
                alignItems='center'
              >
                <Typography variant='h6'>
                  已选择 {selectedCoreProducts.length} 个核心商品 和{' '}
                  {selectedPrintifyProducts.length} 个 Printify 商品
                </Typography>
                <Button
                  variant='contained'
                  startIcon={<LinkIcon />}
                  onClick={handleCreateMapping}
                  sx={{ bgcolor: 'white', color: 'primary.main' }}
                >
                  创建映射
                </Button>
              </Box>
            </CardContent>
          </Card>
        )}

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          gap: 2,
          alignItems: 'stretch',
        }}
      >
        {/* 核心商品列表 - 左侧 */}
        <Box sx={{ flex: { sm: '1 1 0%' }, minWidth: { sm: 0 }, display: 'flex', flexDirection: 'column' }}>
          <Card sx={{ height: '100%', minHeight: 420, display: 'flex', flexDirection: 'column' }}>
            <CardContent>
              <Typography variant='h6' component='h2' mb={2}>
                核心商品
                {showOnlyUnmappedCore && (
                  <Typography component='span' variant='body2' color='text.secondary' sx={{ ml: 1 }}>
                    （仅未映射 {filteredCoreProducts.length}）
                  </Typography>
                )}
              </Typography>

              <TextField
                fullWidth
                placeholder='搜索核心商品...'
                value={coreSearchTerm}
                onChange={e => setCoreSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position='start'>
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ mb: 2 }}
              />

              <TableContainer
                component={Paper}
                variant='outlined'
                sx={{ maxHeight: 420 }}
              >
                <Table stickyHeader size='small'>
                  <TableHead>
                    <TableRow>
                      <TableCell padding='checkbox'>选择</TableCell>
                      <TableCell>商品名称</TableCell>
                      <TableCell>供应商</TableCell>
                      <TableCell>状态</TableCell>
                      <TableCell>变体数</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredCoreProducts.map(product => (
                      <TableRow key={product.id_hashid} hover>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            checked={selectedCoreProducts.includes(
                              product.id_hashid
                            )}
                            onChange={() =>
                              handleCoreProductSelect(product.id_hashid)
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2' fontWeight='medium'>
                            {product.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.vendor}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={product.status}
                            color={product.is_active ? 'success' : 'default'}
                            size='small'
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.variants?.length || 0}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>

        {/* Printify 商品列表 - 右侧 */}
        <Box sx={{ flex: { sm: '1 1 0%' }, minWidth: { sm: 0 }, display: 'flex', flexDirection: 'column' }}>
          <Card sx={{ height: '100%', minHeight: 420, display: 'flex', flexDirection: 'column' }}>
            <CardContent>
              <Typography variant='h6' component='h2' mb={1}>
                Printify 商品
                {showOnlyUnmappedPrintify && (
                  <Typography component='span' variant='body2' color='text.secondary' sx={{ ml: 1 }}>
                    （仅未映射 {filteredPrintifyProducts.length}）
                  </Typography>
                )}
              </Typography>
              <FormControlLabel
                sx={{ mb: 2, display: 'block' }}
                control={
                  <Checkbox
                    checked={printifyPublishedOnly}
                    onChange={e => setPrintifyPublishedOnly(e.target.checked)}
                  />
                }
                label='仅已发布（默认只显示当前店铺且已发布商品）'
              />

              <TextField
                fullWidth
                placeholder='搜索 Printify 商品...'
                value={printifySearchTerm}
                onChange={e => setPrintifySearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position='start'>
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ mb: 2 }}
              />

              <TableContainer
                component={Paper}
                variant='outlined'
                sx={{ maxHeight: 420 }}
              >
                <Table stickyHeader size='small'>
                  <TableHead>
                    <TableRow>
                      <TableCell padding='checkbox'>选择</TableCell>
                      <TableCell>商品名称</TableCell>
                      <TableCell>价格</TableCell>
                      <TableCell>变体数</TableCell>
                      <TableCell>状态</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredPrintifyProducts.map(product => (
                      <TableRow key={product.id} hover>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            checked={selectedPrintifyProducts.includes(
                              product.id
                            )}
                            onChange={() =>
                              handlePrintifyProductSelect(product.id)
                            }
                          />
                        </TableCell>
                        <TableCell>
                          {product.printify_product_id ? (
                            <Link
                              href={`https://printify.com/app/product-details/${product.printify_product_id}?fromProductsPage=1`}
                              target='_blank'
                              rel='noopener noreferrer'
                              variant='body2'
                              fontWeight='medium'
                              sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
                            >
                              {product.title}
                              <OpenInNewIcon sx={{ fontSize: 14 }} />
                            </Link>
                          ) : (
                            <Typography variant='body2' fontWeight='medium'>
                              {product.title}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {getProductPriceRange(product)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.variants?.length ?? 0}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={product.is_published !== false ? '已发布' : '未发布'}
                            color={product.is_published !== false ? 'success' : 'default'}
                            size='small'
                          />
                          {product.printify_shop_id && (
                            <Typography component='span' variant='caption' color='text.secondary' sx={{ ml: 0.5 }}>
                              · {product.printify_shop_id}
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* 现有映射列表 */}
      {mappings.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Box
              display='flex'
              alignItems='center'
              justifyContent='space-between'
              flexWrap='wrap'
              gap={2}
              mb={2}
            >
              <Typography variant='h6' component='h2'>
                现有映射关系
              </Typography>
              {selectedMappingIds.length > 0 && (
                <Stack direction='row' alignItems='center' spacing={2}>
                  <Typography variant='body2' color='text.secondary'>
                    已选 {selectedMappingIds.length} 条
                  </Typography>
                  <Button
                    variant='outlined'
                    color='error'
                    size='small'
                    startIcon={<DeleteIcon />}
                    onClick={() => {
                      if (
                        window.confirm(
                          `确定删除选中的 ${selectedMappingIds.length} 条映射吗？`
                        )
                      ) {
                        handleRemoveMappings(selectedMappingIds);
                      }
                    }}
                  >
                    批量删除
                  </Button>
                  <Button
                    size='small'
                    onClick={() => setSelectedMappingIds([])}
                  >
                    取消选择
                  </Button>
                </Stack>
              )}
            </Box>

            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell padding='checkbox'>
                      <Checkbox
                        indeterminate={
                          someCurrentPageSelected && !allCurrentPageSelected
                        }
                        checked={allCurrentPageSelected}
                        onChange={handleToggleSelectAllMappings}
                        aria-label='全选当前页'
                      />
                    </TableCell>
                    <TableCell>核心商品</TableCell>
                    <TableCell>Printify 商品</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>创建时间</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {currentPageMappings.map(mapping => (
                    <TableRow key={mapping.id} hover>
                      <TableCell padding='checkbox'>
                        <Checkbox
                          checked={selectedMappingIds.includes(
                            mapping.id_hashid
                          )}
                          onChange={() =>
                            handleToggleSelectMapping(mapping.id_hashid)
                          }
                          aria-label={`选择 ${mapping.core_product_title}`}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {mapping.core_product_title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.printify_product_title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={
                            mapping.sync_status === 'active'
                              ? '活跃'
                              : mapping.sync_status === 'pending'
                                ? '待处理'
                                : '错误'
                          }
                          color={
                            mapping.sync_status === 'active'
                              ? 'success'
                              : mapping.sync_status === 'pending'
                                ? 'warning'
                                : 'error'
                          }
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {new Date(mapping.created_at).toLocaleDateString(
                            'zh-CN'
                          )}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={1}>
                          <Tooltip title='查看详情'>
                            <IconButton
                              size='small'
                              onClick={() => handleViewMappingDetail(mapping)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='同步映射'>
                            <IconButton
                              size='small'
                              onClick={() =>
                                handleSyncMapping(mapping.id_hashid)
                              }
                            >
                              <SyncIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='更新状态'>
                            <IconButton
                              size='small'
                              onClick={() => {
                                const newStatus =
                                  mapping.sync_status === 'active'
                                    ? 'pending'
                                    : 'active';
                                handleUpdateMappingStatus(
                                  mapping.id_hashid,
                                  newStatus
                                );
                              }}
                            >
                              {mapping.sync_status === 'active' ? (
                                <InactiveIcon />
                              ) : (
                                <ActiveIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='删除映射'>
                            <IconButton
                              size='small'
                              color='error'
                              onClick={() =>
                                handleRemoveMapping(mapping.id_hashid)
                              }
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            {mappings.length > mappingRowsPerPage && (
              <Box
                display='flex'
                justifyContent='center'
                alignItems='center'
                py={2}
                gap={1}
              >
                <Pagination
                  count={Math.ceil(mappings.length / mappingRowsPerPage)}
                  page={mappingListPage}
                  onChange={(_, p) => setMappingListPage(p)}
                  color='primary'
                  showFirstButton
                  showLastButton
                />
                <Typography variant='body2' color='text.secondary'>
                  共 {mappings.length} 条，第{' '}
                  {(mappingListPage - 1) * mappingRowsPerPage + 1}–
                  {Math.min(
                    mappingListPage * mappingRowsPerPage,
                    mappings.length
                  )}{' '}
                  条
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* 映射确认对话框 */}
      <Dialog
        open={mappingDialogOpen}
        onClose={() => {
          setMappingDialogOpen(false);
          setMappingValidation(null);
        }}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>确认创建映射</DialogTitle>
        <DialogContent>
          <Typography variant='body2' mb={2}>
            您即将创建核心商品与 Printify 商品的映射关系（商品级，不区分变体）。
          </Typography>
          <Alert severity='info' sx={{ mb: 2 }}>
            履约时系统会按「核心变体 SKU」在 Printify 该商品的变体中匹配；若两边变体数一致且 SKU 一致，即可正确发货。若 SKU 不一致，需在商品管理或后续流程中补充变体级映射。
          </Alert>

          {mappingValidation && mappingValidation.warnings.length > 0 && (
            <Alert severity='warning' sx={{ mb: 2 }}>
              <Typography variant='subtitle2' gutterBottom>
                一致性校验：存在以下差异，是否仍要映射？
              </Typography>
              <Box component='ul' sx={{ m: 0, pl: 2 }}>
                {mappingValidation.warnings.map((w, i) => (
                  <li key={i}>
                    <Typography variant='body2'>{w}</Typography>
                  </li>
                ))}
              </Box>
              <Typography variant='body2' sx={{ mt: 1 }}>
                若确认是同一商品或可接受差异，可点击「强制映射」继续创建。
              </Typography>
            </Alert>
          )}

          {mappingValidation && mappingValidation.warnings.length === 0 && (
            <Alert severity='success' sx={{ mb: 2 }}>
              标题与变体维度一致或近似，可放心创建映射。
            </Alert>
          )}

          {selectedCoreProduct && (
            <Box mb={2}>
              <Typography variant='subtitle2' gutterBottom>
                核心商品：
              </Typography>
              <Typography variant='body2'>
                {selectedCoreProduct.title}
              </Typography>
              {mappingValidation && (
                <Typography variant='caption' color='text.secondary'>
                  变体数：{mappingValidation.variantCountCore}
                </Typography>
              )}
            </Box>
          )}

          {selectedPrintifyProduct && (
            <Box mb={2}>
              <Typography variant='subtitle2' gutterBottom>
                Printify 商品：
              </Typography>
              <Typography variant='body2'>
                {selectedPrintifyProduct.title}
              </Typography>
              {mappingValidation && (
                <Typography variant='caption' color='text.secondary'>
                  变体数：{mappingValidation.variantCountPrintify}
                </Typography>
              )}
            </Box>
          )}

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>映射状态</InputLabel>
            <Select
              value={mappingStatus}
              onChange={e =>
                setMappingStatus(e.target.value as 'active' | 'pending')
              }
              label='映射状态'
            >
              <MenuItem value='active'>活跃</MenuItem>
              <MenuItem value='pending'>待处理</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setMappingDialogOpen(false);
              setMappingValidation(null);
            }}
          >
            取消
          </Button>
          <Button
            onClick={handleConfirmMapping}
            variant='contained'
            color={mappingValidation?.warnings?.length ? 'warning' : 'primary'}
          >
            {mappingValidation?.warnings?.length ? '强制映射' : '确认创建'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 映射详情对话框 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth='md'
        fullWidth
      >
        <DialogTitle>映射详情</DialogTitle>
        <DialogContent>
          {selectedMapping && (
            <Box>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box sx={{ width: "100%" }} md={6}>
                  <Card variant='outlined'>
                    <CardContent>
                      <Typography variant='h6' gutterBottom>
                        核心商品
                      </Typography>
                      <Typography variant='body2' fontWeight='medium'>
                        {selectedMapping.core_product_title}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        SKU: {selectedMapping.core_variant_sku || 'N/A'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
                <Box sx={{ width: "100%" }} md={6}>
                  <Card variant='outlined'>
                    <CardContent>
                      <Typography variant='h6' gutterBottom>
                        Printify 商品
                      </Typography>
                      <Typography variant='body2' fontWeight='medium'>
                        {selectedMapping.printify_product_title}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        SKU: {selectedMapping.printify_variant_sku || 'N/A'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              </Box>

              <Box mt={2}>
                <Typography variant='h6' gutterBottom>
                  映射信息
                </Typography>
                <TableContainer component={Paper} variant='outlined'>
                  <Table size='small'>
                    <TableBody>
                      <TableRow>
                        <TableCell>映射类型</TableCell>
                        <TableCell>{selectedMapping.mapping_type}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>同步方向</TableCell>
                        <TableCell>{selectedMapping.sync_direction}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>同步状态</TableCell>
                        <TableCell>
                          <Chip
                            label={selectedMapping.sync_status}
                            color={
                              selectedMapping.sync_status === 'active'
                                ? 'success'
                                : 'warning'
                            }
                            size='small'
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>创建时间</TableCell>
                        <TableCell>
                          {new Date(selectedMapping.created_at).toLocaleString(
                            'zh-CN'
                          )}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>更新时间</TableCell>
                        <TableCell>
                          {new Date(selectedMapping.updated_at).toLocaleString(
                            'zh-CN'
                          )}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              if (selectedMapping) {
                const newStatus =
                  selectedMapping.sync_status === 'active'
                    ? 'pending'
                    : 'active';
                handleUpdateMappingStatus(selectedMapping.id_hashid, newStatus);
              }
            }}
            startIcon={
              selectedMapping?.sync_status === 'active' ? (
                <InactiveIcon />
              ) : (
                <ActiveIcon />
              )
            }
          >
            {selectedMapping?.sync_status === 'active'
              ? '设为待处理'
              : '设为活跃'}
          </Button>
          <Button
            onClick={() => {
              if (selectedMapping) {
                handleSyncMapping(selectedMapping.id_hashid);
              }
            }}
            startIcon={<SyncIcon />}
            variant='outlined'
          >
            同步映射
          </Button>
          <Button onClick={() => setDetailDialogOpen(false)}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* 批量映射对话框 */}
      <BatchMappingDialog
        open={batchDialogOpen}
        onClose={() => setBatchDialogOpen(false)}
        coreProducts={selectedCoreProducts
          .map(id => coreProducts.find(p => p.id_hashid === id)!)
          .filter(Boolean)}
        externalProducts={selectedPrintifyProducts
          .map(id => printifyProducts.find(p => p.id === id)!)
          .filter(Boolean)}
        platform='Printify'
        onConfirm={handleBatchMappingConfirm}
        onCancel={handleBatchMappingCancel}
      />

      {/* 变体映射对话框 */}
      {selectedCoreProduct && selectedPrintifyProduct && (
        <VariantMappingDialog
          open={variantMappingDialogOpen}
          onClose={() => {
            setVariantMappingDialogOpen(false);
            setMappingValidation(null);
          }}
          onConfirm={handleConfirmVariantMapping}
          coreProduct={selectedCoreProduct}
          printifyProduct={selectedPrintifyProduct}
          printifySystemId={printifySystemId}
          validationWarnings={mappingValidation?.warnings}
        />
      )}
    </Box>
  );
}
