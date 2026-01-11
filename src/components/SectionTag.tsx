import "../styles/SectionTag.css";
type Props = {
  tag: string;
};

export default function SectionTag({ tag }: Props) {
  return <div className="section-tag">{tag}</div>;
}
