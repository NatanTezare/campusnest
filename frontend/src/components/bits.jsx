import { fileUrl } from '../api'

const GRADIENTS = [
  'linear-gradient(135deg,#2B3990,#5B6BD0)', 'linear-gradient(135deg,#FFCB05,#FFE27A)',
  'linear-gradient(135deg,#2B3990,#FFCB05)', 'linear-gradient(135deg,#5B6BD0,#E8F4FF)',
  'linear-gradient(135deg,#FFCB05,#2B3990)',
]

/** Hostel photo (first uploaded image) or a themed gradient placeholder. */
export function photoStyle(hostel, i = 0) {
  const url = hostel.photos?.[i]
  return url ? { backgroundImage: `url(${fileUrl(url)})` } : { background: GRADIENTS[hostel.id % GRADIENTS.length] }
}

export const Stars = ({ value }) => {
  const n = Math.round(value || 0)
  return <span className="stars">{'★'.repeat(n)}{'☆'.repeat(5 - n)}</span>
}

export const AvailabilityPill = ({ available }) => (
  <span className={`pill ${available ? 'green' : 'red'}`}>{available ? 'Available' : 'Fully booked'}</span>
)

export function AmenityChips({ selected, onToggle, items }) {
  return (
    <div className="chips">
      {items.map((a) => (
        <button type="button" key={a} className={`chip ${selected.includes(a) ? 'on' : ''}`}
          onClick={() => onToggle(a)}>{a}</button>
      ))}
    </div>
  )
}
