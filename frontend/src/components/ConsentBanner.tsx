import { useEffect, useState } from 'react';

const STORAGE_KEY = 'octivary-consent';

export default function ConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      setVisible(true);
    }
  }, []);

  if (!visible) {
    return null;
  }

  const handleChoice = (value: 'declined' | 'accepted') => {
    localStorage.setItem(STORAGE_KEY, value);
    setVisible(false);
  };

  return (
    <div className="consent-banner">
      <div>
        <strong>Anonymous priorities</strong>
        <p>
          We collect anonymized priority data to improve recommendations. You can opt out at any time.
        </p>
      </div>
      <div className="consent-actions">
        <button className="ghost" onClick={() => handleChoice('declined')}>
          Decline
        </button>
        <button className="cta" onClick={() => handleChoice('accepted')}>
          Accept
        </button>
      </div>
    </div>
  );
}
