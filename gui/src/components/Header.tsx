export default function Header({ title }: { title: string }) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-semibold">{title}</h2>
    </div>
  )
}