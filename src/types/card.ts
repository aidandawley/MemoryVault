// data utilized in Card component

export type CardPublic = {
  media_type: string;
  cardId: string;
  media_id: string;
  caption: string;
  tags: string[];
  /** tags after the backend's normalize_and_alias; the key tag rows group by */
  normalized_tags?: string[];
  isActive: boolean;
};
