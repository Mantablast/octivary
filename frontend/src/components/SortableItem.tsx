import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

type SortableItemProps = {
  id: string;
  children: (props: {
    handleProps: {
      ref: (el: HTMLElement | null) => void;
      listeners: unknown;
      attributes: React.HTMLAttributes<HTMLElement>;
    };
  }) => React.ReactNode;
};

export default function SortableItem({ id, children }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, setActivatorNodeRef } =
    useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      {children({
        handleProps: {
          ref: setActivatorNodeRef,
          listeners,
          attributes
        }
      })}
    </div>
  );
}
