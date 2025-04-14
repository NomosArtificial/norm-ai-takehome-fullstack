'use client';

import HeaderNav from '@/components/HeaderNav';
import SearchComponent from '@/components/SearchComponent';
import { Box } from '@chakra-ui/react';

export default function Page() {
  return (
    <Box minH="100vh" bg="#F7FAFC">
      <HeaderNav signOut={() => {}} />
      <Box pt={6}>
        <SearchComponent />
      </Box>
    </Box>
  );
}
