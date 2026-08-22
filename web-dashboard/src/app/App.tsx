import { BrowserRouter } from 'react-router-dom'

import { Providers } from '@/app/providers'
import { Router } from '@/app/router'

export default function App() {
  return (
    <Providers>
      <BrowserRouter>
        <Router />
      </BrowserRouter>
    </Providers>
  )
}
