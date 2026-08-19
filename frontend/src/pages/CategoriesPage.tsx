import { useState, type FormEvent } from 'react'
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
  type Category,
} from '../api/categories'

function CreateCategoryForm() {
  const [name, setName] = useState('')
  const createCategory = useCreateCategory()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    createCategory.mutate({ name: name.trim() }, { onSuccess: () => setName('') })
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex flex-wrap gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Category name (e.g. Salary, Food)"
        className="flex-1 min-w-40 rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <button
        type="submit"
        disabled={createCategory.isPending}
        className="rounded-lg bg-accent px-4 py-2 font-semibold text-black transition-colors hover:bg-accent-hover disabled:opacity-50"
      >
        Add
      </button>
    </form>
  )
}

function CategoryRow({ category }: { category: Category }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(category.name)
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()

  function handleSave() {
    if (!name.trim() || name === category.name) {
      setEditing(false)
      return
    }
    updateCategory.mutate(
      { id: category.id, payload: { name: name.trim() } },
      { onSuccess: () => setEditing(false) },
    )
  }

  return (
    <li className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface p-3">
      {editing ? (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          className="flex-1 rounded border border-border bg-surface-alt px-2 py-1 text-text focus:border-accent focus:outline-none"
        />
      ) : (
        <span className="flex-1 text-text">{category.name}</span>
      )}
      <div className="flex gap-3 text-sm font-medium">
        {editing ? (
          <button onClick={handleSave} className="text-accent hover:text-accent-hover">
            Save
          </button>
        ) : (
          <button onClick={() => setEditing(true)} className="text-text-muted hover:text-text">
            Edit
          </button>
        )}
        <button
          onClick={() => deleteCategory.mutate(category.id)}
          className="text-negative hover:text-negative/80"
        >
          Delete
        </button>
      </div>
    </li>
  )
}

export function CategoriesPage() {
  const { data: categories, isLoading, isError } = useCategories()

  return (
    <div className="mx-auto max-w-xl">
      <h2 className="mb-4 text-xl font-bold text-text">Categories</h2>
      <CreateCategoryForm />
      {isLoading && <p className="text-text-muted">Loading…</p>}
      {isError && <p className="text-negative">Failed to load categories.</p>}
      {categories && categories.length === 0 && (
        <p className="text-text-muted">No categories yet.</p>
      )}
      <ul className="flex flex-col gap-2">
        {categories?.map((category) => (
          <CategoryRow key={category.id} category={category} />
        ))}
      </ul>
    </div>
  )
}
