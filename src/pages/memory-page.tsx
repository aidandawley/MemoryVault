import Carousel, { type CarouselItem } from "../components/memorypage/Carousel";

export default function MemoryPage() {

  const featured: CarouselItem[] = [
    {
      id: "0",
      title: "Trip to Big Bear",
      creator: "Aidan",
      type: "photo",
      thumbnailUrl: "src/assets/dog1.jpg",
      videoUrl: "src/assets/dog1.jpg",
    },
    {
      id: "1",
      title: "Friends Night Out",
      creator: "Group Vault",
      type: "photo",
      thumbnailUrl: "src/assets/dog3.jpg",
      photoUrl: "src/assets/dog3.jpg",
    },
    {
      id: "2",
      title: "Bob’s B-Day",
      creator: "Group Vault",
      type: "photo",
      thumbnailUrl: "src/assets/dog2.jpg",
      photoUrl: "src/assets/dog2.jpg",
    },
  ];

  return (
    <div>
      <Carousel items={featured} initialIndex={0} radius={2} />
      {/* Rest of your memory page content below */}
    </div>
  );
}
