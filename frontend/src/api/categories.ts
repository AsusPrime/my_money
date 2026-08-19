import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { apiClient } from './client'
import { getErrorMessage } from './errors'

export interface Category {
  id: number
  name: string
}

export interface CategoryCreatePayload {
  name: string
}

export interface CategoryUpdatePayload {
  name?: string
}

const CATEGORIES_KEY = ['categories']

async function fetchCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<{ items: Category[] }>('/categories')
  return data.items
}

async function createCategory(payload: CategoryCreatePayload): Promise<Category> {
  const { data } = await apiClient.post<Category>('/categories', payload)
  return data
}

async function updateCategory(id: number, payload: CategoryUpdatePayload): Promise<Category> {
  const { data } = await apiClient.patch<Category>(`/categories/${id}`, payload)
  return data
}

async function deleteCategory(id: number): Promise<void> {
  await apiClient.delete(`/categories/${id}`)
}

export function useCategories() {
  return useQuery({ queryKey: CATEGORIES_KEY, queryFn: fetchCategories })
}

export function useCreateCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCategory,
    onSuccess: (category) => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_KEY })
      toast.success(`Category "${category.name}" created`)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useUpdateCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CategoryUpdatePayload }) =>
      updateCategory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_KEY })
      toast.success('Category updated')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

export function useDeleteCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_KEY })
      toast.success('Category deleted')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}
