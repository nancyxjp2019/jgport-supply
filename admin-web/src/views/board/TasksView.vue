<template>
  <div class="page-stack">
    <ElAlert v-if="boardError" class="page-alert" type="error" :closable="false" :title="boardError" />

    <div v-if="boardLoading" class="skeleton-grid">
      <ElSkeleton v-for="index in 3" :key="index" animated>
        <template #template>
          <div class="skeleton-card skeleton-card--tall"></div>
        </template>
      </ElSkeleton>
    </div>

    <template v-else-if="board">
      <section class="task-overview-grid">
        <article class="signal-card signal-card--warning">
          <span>待补录金额</span>
          <strong>{{ board.pending_supplement_count }}</strong>
          <p>优先跟进缺金额、缺凭证的资金单据</p>
        </article>
        <article class="signal-card signal-card--danger">
          <span>校验失败</span>
          <strong>{{ board.validation_failed_count }}</strong>
          <p>重点检查超阈值与数量校验失败的库存单据</p>
        </article>
        <article class="signal-card signal-card--accent">
          <span>数量履约完成未关闭</span>
          <strong>{{ board.qty_done_not_closed_count }}</strong>
          <p>优先检查金额闭环差额与关闭阻塞原因</p>
        </article>
        <article class="signal-card signal-card--deep">
          <span>履约滞留</span>
          <strong>{{ board.fulfillment_stagnant_count }}</strong>
          <p>重点跟进连续 3 个上海自然日无新履约累计的合同</p>
        </article>
      </section>

      <ElTabs class="board-tabs">
        <ElTabPane label="资金待办">
          <div class="task-list">
            <article v-for="item in board.pending_supplement_items" :key="`${item.biz_type}-${item.biz_id}`" class="task-card">
              <div class="task-card__header">
                <strong>{{ item.title }}</strong>
                <ElTag type="warning" round>{{ item.status }}</ElTag>
              </div>
              <p>关联合同：{{ item.contract_no || '未关联' }}</p>
              <p>创建时间：{{ formatDateTime(item.created_at) }}</p>
            </article>
            <ElEmpty v-if="!board.pending_supplement_items.length" description="当前暂无资金待办" />
          </div>
        </ElTabPane>

        <ElTabPane label="库存阻塞">
          <div class="task-list">
            <article v-for="item in board.validation_failed_items" :key="`${item.biz_type}-${item.biz_id}`" class="task-card">
              <div class="task-card__header">
                <strong>{{ item.title }}</strong>
                <ElTag type="danger" round>{{ item.status }}</ElTag>
              </div>
              <p>关联合同：{{ item.contract_no || '未关联' }}</p>
              <p>创建时间：{{ formatDateTime(item.created_at) }}</p>
            </article>
            <ElEmpty v-if="!board.validation_failed_items.length" description="当前暂无库存阻塞" />
          </div>
        </ElTabPane>

        <ElTabPane label="合同待关闭">
          <div class="task-list">
            <article v-for="item in board.qty_done_not_closed_items" :key="`${item.biz_type}-${item.biz_id}`" class="task-card">
              <div class="task-card__header">
                <strong>{{ item.title }}</strong>
                <ElTag type="info" round>{{ item.status }}</ElTag>
              </div>
              <p>合同编号：{{ item.contract_no || '未关联' }}</p>
              <p>最近时间：{{ formatDateTime(item.created_at) }}</p>
            </article>
            <ElEmpty v-if="!board.qty_done_not_closed_items.length" description="当前暂无待关闭合同" />
          </div>
        </ElTabPane>

        <ElTabPane label="履约滞留">
          <div class="task-list">
            <article v-for="item in board.fulfillment_stagnant_items" :key="`${item.biz_type}-${item.biz_id}`" class="task-card">
              <div class="task-card__header">
                <strong>{{ item.title }}</strong>
                <ElTag type="danger" round>{{ item.scan_type || item.status }}</ElTag>
              </div>
              <p>合同编号：{{ item.contract_no || '未关联' }}</p>
              <p>最近履约时间：{{ formatDateTime(item.last_effect_at || item.created_at) }}</p>
              <p>滞留天数：{{ item.days_without_effect ?? 0 }} 天</p>
            </article>
            <ElEmpty v-if="!board.fulfillment_stagnant_items.length" description="当前暂无履约滞留合同" />
          </div>
        </ElTabPane>
      </ElTabs>
    </template>

    <ElEmpty v-else description="暂无业务看板数据" />
  </div>
</template>

<script setup lang="ts">
import { ElAlert, ElEmpty, ElSkeleton, ElTabPane, ElTabs, ElTag } from 'element-plus'
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import { useReportStore } from '@/stores/report'
import { formatDateTime } from '@/utils/formatters'

const reportStore = useReportStore()
const { board, boardError, boardLoading } = storeToRefs(reportStore)

onMounted(async () => {
  if (!board.value && !boardLoading.value) {
    await reportStore.loadBoard()
  }
})
</script>
