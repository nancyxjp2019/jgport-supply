import { describe, expect, it } from 'vitest'

import {
  approveDemoContract,
  getDemoContractDetail,
  listDemoContracts,
  submitDemoContract,
  updateDemoContract,
} from '@/mock/contracts'

describe('合同管理台演示数据', () => {
  it('可按方向筛选采购合同', () => {
    const response = listDemoContracts({ direction: 'purchase' })
    expect(response.total).toBeGreaterThan(0)
    expect(response.items.every((item) => item.direction === 'purchase')).toBe(true)
  })

  it('退回草稿可修改并保留退回意见', () => {
    const updated = updateDemoContract(5401, {
      contract_no: 'CODEX-TEST-DEMO-CONTRACT-5401',
      supplier_id: 'CODEX-TEST-SUPPLIER-EDIT-5401',
      items: [{ oil_product_id: 'OIL-95', qty_signed: 88.8, unit_price: 6210.5 }],
    })
    expect(updated.status).toBe('草稿')
    expect(updated.approval_comment).toBe('AUTO-TEST-资料不完整，退回修改')
    expect(updated.contract_no).toBe('CODEX-TEST-DEMO-CONTRACT-5401')
  })

  it('草稿修改后可再次提审并审批生效', () => {
    const submitted = submitDemoContract(5401, { comment: 'CODEX-TEST-修改后再次提审' })
    expect(submitted.status).toBe('待审批')
    expect(submitted.submit_comment).toBe('CODEX-TEST-修改后再次提审')

    const approved = approveDemoContract(5401, {
      approval_result: true,
      comment: 'CODEX-TEST-审批通过',
    })
    expect(approved.status).toBe('生效中')
    expect(approved.generated_task_count).toBeGreaterThan(0)

    const detail = getDemoContractDetail(5401)
    expect(detail.status).toBe('生效中')
  })
})
