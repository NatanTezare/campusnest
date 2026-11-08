import { useNavigate } from 'react-router-dom'

export default function Hero({ brand, title, sub, back, backTo }) {
  const nav = useNavigate()
  return (
    <div className="hero">
      {back && <button className="back" onClick={() => (backTo ? nav(backTo) : nav(-1))}>‹ {back}</button>}
      {brand && <div className="brand">{brand}</div>}
      <h1>{title}</h1>
      {sub && <p>{sub}</p>}
    </div>
  )
}
