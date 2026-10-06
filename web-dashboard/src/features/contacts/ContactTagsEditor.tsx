import { Plus, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useDanhSachTheQuery,
  useGanTheMutation,
  useGoTheMutation,
  useTaoTheMutation,
} from '@/api/contacts'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import type { The } from '@/types/schema'
import { boDau } from '@/utils/ten'

/**
 * UC017 — gắn / gỡ / tạo thẻ trên hồ sơ khách.
 *
 * Tự lọc bằng `boDau` thay vì bộ lọc mờ của cmdk: cmdk không bỏ dấu, gõ "vip" sẽ không ra
 * "Khách VIP" nếu người dùng gõ "khach". Mục "Tạo thẻ" chỉ hiện khi tên sau khi bỏ dấu chưa
 * trùng thẻ nào — máy chủ cũng chống trùng theo đúng phép này, trùng thì trả thẻ cũ.
 */
export function ContactTagsEditor({
  contactId,
  dangGan,
  chiDoc,
}: {
  contactId: string
  dangGan: The[]
  /** Hồ sơ đã hợp nhất / ẩn danh hoá — máy chủ từ chối ghi, nên ẩn hẳn thao tác. */
  chiDoc: boolean
}) {
  const [mo, datMo] = useState(false)
  const [tuKhoa, datTuKhoa] = useState('')
  const tatCa = useDanhSachTheQuery(undefined, { skip: chiDoc })
  const [taoThe, ketQuaTao] = useTaoTheMutation()
  const [ganThe, ketQuaGan] = useGanTheMutation()
  const [goThe] = useGoTheMutation()

  const idDangGan = new Set(dangGan.map((t) => t.id))
  const khoa = boDau(tuKhoa)
  const conLai = (tatCa.data ?? []).filter(
    (t) => !idDangGan.has(t.id) && (khoa === '' || boDau(t.name).includes(khoa)),
  )
  const trungTen = (tatCa.data ?? []).some((t) => boDau(t.name) === khoa)
  const dangBan = ketQuaTao.isLoading || ketQuaGan.isLoading

  async function gan(the: The) {
    try {
      await ganThe({ contactId, tagId: the.id }).unwrap()
      toast.success(`Đã gắn thẻ "${the.name}".`)
      datTuKhoa('')
      datMo(false)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không gắn được thẻ.')
    }
  }

  async function taoVaGan() {
    const ten = tuKhoa.trim()
    if (!ten) return
    try {
      const the = await taoThe({ name: ten }).unwrap()
      await gan(the)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không tạo được thẻ.')
    }
  }

  async function go(the: The) {
    try {
      await goThe({ contactId, tagId: the.id }).unwrap()
      toast.success(`Đã gỡ thẻ "${the.name}".`)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không gỡ được thẻ.')
    }
  }

  if (chiDoc && dangGan.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-muted-foreground text-xs font-medium">Thẻ</span>
      <div className="flex flex-wrap items-center gap-1.5">
        {dangGan.map((t) => (
          <span
            key={t.id}
            className="bg-secondary text-secondary-foreground inline-flex h-6 items-center gap-1.5 rounded-full pr-1 pl-2.5 text-xs font-medium"
          >
            {/* Màu thẻ là DỮ LIỆU doanh nghiệp (máy chủ tự gán từ bảng 8 màu) — chấm màu đi kèm
                tên chữ nên không truyền đạt chỉ bằng màu. */}
            <span
              aria-hidden
              className="size-2 shrink-0 rounded-full"
              style={{ backgroundColor: t.color ?? 'var(--muted-foreground)' }}
            />
            {t.name}
            {!chiDoc && (
              <button
                type="button"
                aria-label={`Gỡ thẻ ${t.name}`}
                onClick={() => go(t)}
                className="text-muted-foreground hover:text-foreground focus-visible:ring-ring/50 rounded-full p-0.5 outline-none focus-visible:ring-3"
              >
                <X className="size-3" />
              </button>
            )}
          </span>
        ))}

        {!chiDoc && (
          <Popover open={mo} onOpenChange={datMo}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="xs">
                <Plus />
                Thẻ
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64 p-0" align="start">
              <Command shouldFilter={false}>
                <CommandInput
                  placeholder="Tìm hoặc tạo thẻ…"
                  value={tuKhoa}
                  onValueChange={datTuKhoa}
                  maxLength={50}
                />
                <CommandList>
                  {conLai.length === 0 && khoa === '' && (
                    <CommandEmpty>
                      {tatCa.isLoading ? 'Đang tải…' : 'Gõ tên để tạo thẻ đầu tiên.'}
                    </CommandEmpty>
                  )}
                  {conLai.length > 0 && (
                    <CommandGroup>
                      {conLai.map((t) => (
                        <CommandItem
                          key={t.id}
                          value={t.id}
                          disabled={dangBan}
                          onSelect={() => gan(t)}
                        >
                          <span
                            aria-hidden
                            className="size-2 shrink-0 rounded-full"
                            style={{ backgroundColor: t.color ?? 'var(--muted-foreground)' }}
                          />
                          <span className="truncate">{t.name}</span>
                          <span className="text-muted-foreground ml-auto text-xs tabular-nums">
                            {(t.usageCount ?? 0).toLocaleString('vi-VN')}
                          </span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                  {khoa !== '' && !trungTen && (
                    <CommandGroup>
                      <CommandItem value="__tao__" disabled={dangBan} onSelect={taoVaGan}>
                        <Plus />
                        <span className="truncate">Tạo thẻ "{tuKhoa.trim()}"</span>
                      </CommandItem>
                    </CommandGroup>
                  )}
                  {khoa !== '' && trungTen && conLai.length === 0 && (
                    <CommandEmpty>Thẻ này đã được gắn.</CommandEmpty>
                  )}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        )}
      </div>
    </div>
  )
}
